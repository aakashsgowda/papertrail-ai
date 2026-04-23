from .neo4j_db import get_driver
from .config import settings
from .rag.llm import embed_texts

def retrieve_with_graph(user_id: str, question: str) -> list[dict]:
    drv = get_driver()
    qvec = embed_texts([question])[0]

    # Step 1: vector search
    with drv.session() as s:
        base_res = s.run(
            """
            CALL db.index.vector.queryNodes('chunk_embedding_idx', $k, $qvec)
            YIELD node, score
            WHERE node.user_id = $user_id
            RETURN node.chunk_id AS chunk_id,
                   node.doc_id AS doc_id,
                   node.page AS page,
                   node.text AS text,
                   score AS score
            ORDER BY score DESC
            """,
            k=settings.top_k,
            qvec=qvec,
            user_id=user_id
        )
        base = [dict(r) for r in base_res]

    if not base:
        return []

    base_ids = [b["chunk_id"] for b in base]

    # Step 2: graph traversal expansion
    # Chunk -> Entity -> other Chunks that mention same Entity, all within same user
    with drv.session() as s:
        expand_res = s.run(
            """
            UNWIND $base_ids AS cid
            MATCH (c:Chunk {chunk_id: cid, user_id:$user_id})-[:MENTIONS]->(e:Entity {user_id:$user_id})
            MATCH (c2:Chunk {user_id:$user_id})-[:MENTIONS]->(e)
            WHERE c2.chunk_id <> cid
            RETURN DISTINCT
                   c2.chunk_id AS chunk_id,
                   c2.doc_id AS doc_id,
                   c2.page AS page,
                   c2.text AS text,
                   0.0 AS score
            LIMIT $limit
            """,
            base_ids=base_ids,
            user_id=user_id,
            limit=settings.expand_k
        )
        expanded = [dict(r) for r in expand_res]

    # Step 3: merge unique chunks
    seen = set()
    merged: list[dict] = []

    for item in base + expanded:
        cid = item["chunk_id"]
        if cid in seen:
            continue
        seen.add(cid)
        merged.append(item)

    return merged
