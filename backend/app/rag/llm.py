from collections import defaultdict, deque
from google import genai
from ..config import settings

# In-memory conversation history per user (stores last 10 turns)
_conversation_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=10))

def get_client() -> genai.Client:
  if settings.use_vertex_ai:
    return genai.Client(vertexai=True, project=settings.gcp_project, location=settings.gcp_region)
  return genai.Client(api_key=settings.gemini_api_key)

def embed_texts(texts: list[str]) -> list[list[float]]:

  client = get_client()
  vectors: list[list[float]] = []

  for t in texts:

    resp = client.models.embed_content(model = settings.embed_model, contents = t)

    emb = None

    if hasattr(resp, 'embeddings') and resp.embeddings:
      emb = resp.embeddings[0].values
    elif hasattr(resp, 'embedding'):
      emb = resp.embedding.values

    if emb is None:
      raise RuntimeError("Embedding response format not recognized.")
    
    vectors.append(list(emb))

  return vectors


def get_history(user_id: str) -> list[dict]:
  """Return recent conversation history for a user."""
  return list(_conversation_history[user_id])


def add_to_history(user_id: str, question: str, answer: str):
  """Store a Q&A turn in the user's conversation history."""
  _conversation_history[user_id].append({"question": question, "answer": answer})


def rewrite_query(question: str, user_id: str) -> str:
  """Use conversation history to rewrite a follow-up question into a standalone question."""
  history = get_history(user_id)
  if not history:
    return question

  client = get_client()
  history_text = "\n".join(
    f"User: {h['question']}\nAssistant: {h['answer']}"
    for h in history[-5:]  # last 5 turns
  )

  prompt = f"""
Given the conversation history and a follow-up question, rewrite the follow-up question as a standalone question that includes all necessary context from the conversation. If the question is already standalone, return it as-is.

Conversation history:
{history_text}

Follow-up question: {question}

Rewritten standalone question (return ONLY the rewritten question, nothing else):
""".strip()

  resp = client.models.generate_content(model=settings.gen_model, contents=prompt)
  rewritten = (resp.text if hasattr(resp, "text") and resp.text else str(resp)).strip()
  return rewritten if rewritten else question


def classify_question_intent(question: str) -> str:
  """
  Classify what section of a research paper the question targets.
  Returns one of: "method", "results", "background", "limitations", "general".
  Falls back to "general" on any failure so retrieval always continues.
  """
  client = get_client()

  prompt = f"""
You are a classifier for research paper questions.
Classify the question into exactly ONE of these categories:

- method      : asks about how something was done — approach, algorithm, architecture, training
- results     : asks about performance, metrics, scores, comparisons, what was achieved
- background  : asks about prior work, motivation, definitions, related work, context
- limitations : asks about weaknesses, failure cases, future work, what doesn't work
- general     : does not clearly fit any of the above

Respond with EXACTLY one word from this list: method, results, background, limitations, general

Question: {question}
""".strip()

  try:
    resp = client.models.generate_content(model=settings.gen_model, contents=prompt)
    text = (resp.text if hasattr(resp, "text") and resp.text else "").strip().lower()
    for label in ("method", "results", "background", "limitations"):
      if label in text:
        return label
  except Exception:
    pass
  return "general"


def classify_question(question: str) -> dict:
  """Ask the LLM whether this is a greeting/casual message or a real question needing documents."""
  client = get_client()

  prompt = f"""
You are a classifier. Given a user message, decide if it is:
1. A greeting or casual conversation (e.g. "hello", "hi", "how are you", "what can you do", "thanks")
2. A real question that requires searching through documents

Respond with EXACTLY one word: "greeting" or "question". Nothing else.

User message: {question}
""".strip()

  resp = client.models.generate_content(model=settings.gen_model, contents=prompt)
  text = (resp.text if hasattr(resp, "text") and resp.text else str(resp)).strip().lower()
  return {"type": "greeting" if "greeting" in text else "question"}


def generate_chat_response(question: str) -> str:
  """Let the LLM handle greetings and casual conversation naturally."""
  client = get_client()

  prompt = f"""
You are PaperTrail AI, a document intelligence assistant that uses knowledge graph retrieval to help users analyze their uploaded PDF documents.

Respond to the user's message warmly and concisely. Briefly introduce what you can do if appropriate.

User message: {question}
""".strip()

  resp = client.models.generate_content(model=settings.gen_model, contents=prompt)
  if hasattr(resp, "text") and resp.text:
    return resp.text.strip()
  return str(resp).strip()


def generate_grounded_answer(question: str, context_blocks: list[dict]) -> str:

  client = get_client()
  ctx = "\n\n".join(
        f"[doc={b['doc_id']} page={b.get('page','?')} chunk={b['chunk_id']}]\n{b['text']}"
        for b in context_blocks
    )

  prompt = f"""
    You are a helpful assistant.
    Use only the provided context. If the answer is not in the context, say you don't have enough information.

    Question:
    {question}

    Context:
    {ctx}

    Answer:
    """.strip()
  resp = client.models.generate_content(model=settings.gen_model, contents=prompt)
  if hasattr(resp, "text") and resp.text:
    return resp.text.strip()
  return str(resp).strip()
