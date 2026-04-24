import os
from pydantic import BaseModel

class Settings(BaseModel):
  use_vertex_ai: bool = os.getenv("GOOGLE_GENAI_USE_VERTEX_AI", "False").lower() == "true"
  gcp_project: str | None = os.getenv("GOOGLE_CLOUD_PROJECT")
  gcp_region: str | None = os.getenv("GOOGLE_CLOUD_REGION")
  gemini_api_key: str | None = (os.getenv("GEMINI_API_KEY") or "").strip() or None

  embed_model : str = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
  gen_model : str = os.getenv("GEN_MODEL", "gemini-1.5-flash")

  neo4j_uri: str = os.getenv("NEO4J_URI", '')
  neo4j_user: str = os.getenv("NEO4J_USER",'neo4j')
  neo4j_password: str = os.getenv("NEO4J_PASSWORD",'')

  top_k: int = int(os.getenv("TOP_K", "8"))
  expand_k: int = int(os.getenv("EXPAND_K", "12"))
  vector_fetch_multiplier: int = int(os.getenv("VECTOR_FETCH_MULTIPLIER", "5"))
  max_entity_degree: int = int(os.getenv("MAX_ENTITY_DEGREE", "50"))
  chunk_size: int = int(os.getenv("CHUNK_SIZE", '1200'))
  overlap_size: int = int(os.getenv("CHUNK_OVERLAP", '200'))

  embed_dim: int = int(os.getenv("EMBED_DIM", '768'))

settings = Settings()

