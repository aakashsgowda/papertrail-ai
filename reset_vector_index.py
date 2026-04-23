"""
Script to drop and recreate the vector index with correct dimensions
"""
from dotenv import load_dotenv
load_dotenv()  # Load environment variables first

from app.neo4j_db import get_driver, close_driver
from app.config import settings

def reset_vector_index():
    drv = get_driver()
    with drv.session() as s:
        # Drop existing vector index
        print("Dropping existing vector index...")
        s.run("DROP INDEX chunk_embedding_idx IF EXISTS")

        # Recreate with correct dimensions
        print(f"Creating vector index with {settings.embed_dim} dimensions...")
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
        print("✓ Vector index recreated successfully!")

    close_driver()

if __name__ == "__main__":
    reset_vector_index()
