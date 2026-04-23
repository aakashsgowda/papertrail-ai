"""
Complete reset: drop everything and recreate from scratch
"""
from dotenv import load_dotenv
load_dotenv()

from app.neo4j_db import get_driver, close_driver
from app.config import settings

def full_reset():
    drv = get_driver()

    with drv.session() as s:
        # Show current indexes
        print("Current indexes:")
        result = s.run("SHOW INDEXES")
        for record in result:
            print(f"  - {record['name']}: {record['type']}")

        print("\n1. Deleting all data...")
        s.run("MATCH (n) DETACH DELETE n")

        print("2. Dropping all constraints...")
        constraints = s.run("SHOW CONSTRAINTS").data()
        for constraint in constraints:
            name = constraint['name']
            print(f"   Dropping constraint: {name}")
            s.run(f"DROP CONSTRAINT {name} IF EXISTS")

        print("3. Dropping all indexes...")
        indexes = s.run("SHOW INDEXES").data()
        for index in indexes:
            name = index['name']
            print(f"   Dropping index: {name}")
            s.run(f"DROP INDEX {name} IF EXISTS")

        print("\n4. Recreating schema...")
        # Recreate constraints
        s.run("CREATE CONSTRAINT user_id_unique FOR (u:User) REQUIRE u.user_id IS UNIQUE")
        s.run("CREATE CONSTRAINT doc_id_unique FOR (d:Document) REQUIRE d.doc_id IS UNIQUE")
        s.run("CREATE CONSTRAINT chunk_id_unique FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE")
        s.run("CREATE CONSTRAINT entity_user_name_unique FOR (e:Entity) REQUIRE (e.user_id, e.name) IS UNIQUE")

        # Recreate indexes
        s.run("CREATE INDEX doc_user_idx FOR (d:Document) ON (d.user_id)")
        s.run("CREATE INDEX chunk_user_idx FOR (c:Chunk) ON (c.user_id)")
        s.run("CREATE INDEX chunk_doc_idx FOR (c:Chunk) ON (c.doc_id)")
        s.run("CREATE INDEX entity_user_idx FOR (e:Entity) ON (e.user_id)")

        # Recreate vector index with correct dimensions
        print(f"5. Creating vector index with {settings.embed_dim} dimensions...")
        s.run(
            """
            CREATE VECTOR INDEX chunk_embedding_idx
            FOR (c:Chunk) ON (c.embedding)
            OPTIONS { indexConfig: {
              `vector.dimensions`: $dim,
              `vector.similarity_function`: 'cosine'
            } }
            """,
            dim=settings.embed_dim
        )

        print("\n✓ Full reset complete!")
        print(f"✓ Vector index created with {settings.embed_dim} dimensions")

    close_driver()

if __name__ == "__main__":
    response = input("This will completely reset your database. Continue? (yes/no): ")
    if response.lower() == 'yes':
        full_reset()
        print("\nNow restart your server with: uvicorn app.main:app --reload")
    else:
        print("Operation cancelled.")
