from .neo4j_db import get_driver
from .config import settings

def init_schema():

  drv = get_driver()
  with drv.session() as s:
    s.run("CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE")

    s.run("CREATE CONSTRAINT doc_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE")
    s.run("CREATE INDEX doc_user_idx IF NOT EXISTS FOR (d:Document) ON (d.user_id)")

    s.run("CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE")
    s.run("CREATE INDEX chunk_user_idx IF NOT EXISTS FOR (c:Chunk) ON (c.user_id)")
    s.run("CREATE INDEX chunk_doc_idx IF NOT EXISTS FOR (c:Chunk) ON (c.doc_id)")
    s.run("CREATE INDEX chunk_section_idx IF NOT EXISTS FOR (c:Chunk) ON (c.section)")

    s.run("CREATE CONSTRAINT entity_user_name_unique IF NOT EXISTS FOR (e:Entity) REQUIRE (e.user_id, e.name) IS UNIQUE")
    s.run("CREATE INDEX entity_user_idx IF NOT EXISTS FOR (e:Entity) ON (e.user_id)")

    s.run(
            """
            CREATE VECTOR INDEX chunk_embedding_idx IF NOT EXISTS
            FOR (c:Chunk) ON (c.embedding)
            OPTIONS { indexConfig: {
              `vector.dimensions`: $dim,
              `vector.similarity_function`: 'cosine'
            } }
            """,
            dim=settings.embed_dim
        )








