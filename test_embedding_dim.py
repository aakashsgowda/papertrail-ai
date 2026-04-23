"""
Test to see what dimension embeddings are actually returned
"""
from dotenv import load_dotenv
load_dotenv()

from app.rag.llm import embed_texts

# Test embedding
test_text = "This is a test sentence."
print(f"Testing embedding for: '{test_text}'")

embeddings = embed_texts([test_text])
embedding = embeddings[0]

print(f"\nActual embedding dimension: {len(embedding)}")
print(f"Expected dimension (EMBED_DIM): 768")
print(f"\nFirst 5 values: {embedding[:5]}")
