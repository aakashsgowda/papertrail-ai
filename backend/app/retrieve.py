from .neo4j_db import get_driver
from .config import settings
from .rag.llm import embed_texts, classify_question_intent

# Score added to chunks whose section matches the question's intent.
_SECTION_BOOST = 0.15

# Maps each intent label to the set of canonical section labels that should
# be boosted.  "general" gets no boost — retrieval falls back to pure
# vector + graph scores.
_INTENT_SECTIONS: dict[str, set[str]] = {
    "method":      {"method", "experiments"},
    "results":     {"results", "discussion"},
    "background":  {"abstract", "introduction", "background"},
    "limitations": {"limitations", "conclusion"},
    "general":     set(),
}


def retrieve_with_graph(user_id: str, question: str) -> list[dict]:
    drv = get_driver()
    qvec = embed_texts([question])[0]

    # Step 1: vector search
    # Over-fetch by vector_fetch_multiplier so the post-filter by user_id has
    # enough candidates to return top_k results even when a single large user
    # dominates the global ANN index.
    fetch_k = settings.top_k * settings.vector_fetch_multiplier
    with drv.session() as s:
        base_res = s.run(
            """
            CALL db.index.vector.queryNodes('chunk_embedding_idx', $fetch_k, $qvec)
            YIELD node, score
            WHERE node.user_id = $user_id
            RETURN node.chunk_id AS chunk_id,
                   node.doc_id   AS doc_id,
                   node.page     AS page,
                   node.text     AS text,
                   node.section  AS section,
                   score         AS score
            ORDER BY score DESC
            LIMIT $top_k
            """,
            fetch_k=fetch_k,
            qvec=qvec,
            user_id=user_id,
            top_k=settings.top_k,
        )
        base = [dict(r) for r in base_res]

    if not base:
        return []

    base_ids = [b["chunk_id"] for b in base]

    # Step 2: graph expansion
    # Skip entities whose chunk-degree exceeds max_entity_degree — these are
    # stop-word-like entities (e.g. "Transformer", "neural network") that
    # connect so many chunks that traversal cost outweighs retrieval signal.
    with drv.session() as s:
        expand_res = s.run(
            """
            UNWIND $base_ids AS cid
            MATCH (c:Chunk {chunk_id: cid, user_id: $user_id})-[:MENTIONS]->(e:Entity {user_id: $user_id})
            WHERE size((e)<-[:MENTIONS]-(:Chunk {user_id: $user_id})) <= $max_entity_degree
            MATCH (c2:Chunk {user_id: $user_id})-[:MENTIONS]->(e)
            WHERE c2.chunk_id <> cid
            RETURN DISTINCT
                   c2.chunk_id AS chunk_id,
                   c2.doc_id   AS doc_id,
                   c2.page     AS page,
                   c2.text     AS text,
                   c2.section  AS section,
                   0.0         AS score
            LIMIT $limit
            """,
            base_ids=base_ids,
            user_id=user_id,
            max_entity_degree=settings.max_entity_degree,
            limit=settings.expand_k,
        )
        expanded = [dict(r) for r in expand_res]

    # Step 3: merge — vector results first, graph-expanded results appended
    seen: set[str] = set()
    merged: list[dict] = []

    for item in base + expanded:
        cid = item["chunk_id"]
        if cid in seen:
            continue
        seen.add(cid)
        merged.append(item)

    # Step 4: section-aware re-ranking
    # Classify what part of the paper the question targets, then add a fixed
    # bonus to chunks whose section matches.  Old chunks with section=None
    # are treated as "unknown" and receive no boost.
    intent = classify_question_intent(question)
    boost_sections = _INTENT_SECTIONS.get(intent, set())

    if boost_sections:
        for item in merged:
            section = item.get("section") or "unknown"
            if section in boost_sections:
                item["score"] = (item["score"] or 0.0) + _SECTION_BOOST
        merged.sort(key=lambda x: x["score"], reverse=True)

    return merged
