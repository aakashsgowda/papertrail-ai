import uuid
from ..config import settings
from ..neo4j_db import get_driver
from .pdf import extract_pdf_pages
from .chunking import chunk_text
from .llm import embed_texts
from .entity_extract import extract_entities_from_chunk
from .metadata_extract import extract_paper_metadata, assign_chunk_sections

def ingest_pdf(user_id: str, pdf_path: str, title: str) -> tuple[str, dict]:
    drv = get_driver()
    doc_id = str(uuid.uuid4())

    pages = extract_pdf_pages(pdf_path)
    metadata = extract_paper_metadata(pages)

    chunk_rows: list[dict] = []
    for page_no, page_text in pages:
        for ch in chunk_text(page_text, settings.chunk_size, settings.overlap_size):
            chunk_rows.append({
                "chunk_id": str(uuid.uuid4()),
                "doc_id": doc_id,
                "user_id": user_id,
                "page": page_no,
                "text": ch,
            })

    assign_chunk_sections(pages, chunk_rows)

    with drv.session() as s:
        s.run(
            """
            MERGE (u:User {user_id:$user_id})
            CREATE (d:Document {
                doc_id:       $doc_id,
                user_id:      $user_id,
                title:        $title,
                paper_title:  $paper_title,
                authors:      $authors,
                abstract:     $abstract,
                section_headings: $section_headings
            })
            MERGE (u)-[:OWNS]->(d)
            """,
            user_id=user_id,
            doc_id=doc_id,
            title=title,
            paper_title=metadata["paper_title"],
            authors=metadata["authors"],
            abstract=metadata["abstract"],
            section_headings=metadata["section_headings"],
        )

    if not chunk_rows:
        return doc_id, metadata

    vectors = embed_texts([c["text"] for c in chunk_rows])
    for c, v in zip(chunk_rows, vectors):
        c["embedding"] = v

    with drv.session() as s:
        s.run(
            """
            MATCH (d:Document {doc_id:$doc_id, user_id:$user_id})
            UNWIND $chunks AS c
            CREATE (ch:Chunk {
              chunk_id: c.chunk_id,
              user_id: c.user_id,
              doc_id: c.doc_id,
              page: c.page,
              text: c.text,
              section: c.section,
              embedding: c.embedding
            })
            MERGE (d)-[:HAS_CHUNK]->(ch)
            """,
            doc_id=doc_id,
            user_id=user_id,
            chunks=chunk_rows
        )

    # Entity extraction + graph edges
    # This is the key step that makes it Graph RAG.
    with drv.session() as s:
        for c in chunk_rows:
            entities = extract_entities_from_chunk(c["text"])
            if not entities:
                continue

            s.run(
                """
                MATCH (ch:Chunk {chunk_id:$chunk_id, user_id:$user_id})
                UNWIND $entities AS e
                MERGE (ent:Entity {user_id:$user_id, name:e.name})
                SET ent.type = coalesce(ent.type, e.type)
                MERGE (ch)-[:MENTIONS]->(ent)
                """,
                chunk_id=c["chunk_id"],
                user_id=user_id,
                entities=entities
            )

    return doc_id, metadata
