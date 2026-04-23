import os
import tempfile
import uuid
from dotenv import load_dotenv

load_dotenv()  # must be before importing modules that read env vars

from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schema import init_schema
from .neo4j_db import close_driver, get_driver
from .rag.ingest import ingest_pdf
from .retrieve import retrieve_with_graph
from .rag.llm import generate_grounded_answer, classify_question, generate_chat_response, rewrite_query, add_to_history

app = FastAPI(title="PaperTrail AI")

# For now allow all origins (demo). Later restrict to your frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _resolve_user_id(x_user_id: str | None, form_user_id: str | None) -> str:
    uid = (x_user_id or form_user_id or "").strip()
    if not uid:
        raise HTTPException(
            status_code=400,
            detail="Missing user_id. Send it as X-User-Id header or as form field user_id.",
        )
    return uid

@app.on_event("startup")
def startup():
    init_schema()

@app.on_event("shutdown")
def shutdown():
    close_driver()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/session")
def create_session():
    """
    Frontend will call this once, store returned user_id in localStorage,
    then send it on every request.
    """
    user_id = str(uuid.uuid4())
    return {"user_id": user_id}

@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    user_id: str | None = Form(default=None),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    uid = _resolve_user_id(x_user_id, user_id)

    suffix = os.path.splitext(file.filename or "upload.pdf")[1] or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        doc_id, metadata = ingest_pdf(user_id=uid, pdf_path=tmp_path, title=file.filename or "upload.pdf")
    finally:
        os.unlink(tmp_path)
    return {"doc_id": doc_id, "metadata": metadata}

@app.post("/ask")
async def ask(
    question: str = Form(...),
    user_id: str | None = Form(default=None),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    uid = _resolve_user_id(x_user_id, user_id)

    # Let the LLM classify if this is a greeting or a real question
    classification = classify_question(question)
    if classification["type"] == "greeting":
        answer = generate_chat_response(question)
        add_to_history(uid, question, answer)
        return {"answer": answer, "citations": [], "context": []}

    # Rewrite follow-up questions using conversation history
    standalone_question = rewrite_query(question, uid)

    ctx = retrieve_with_graph(user_id=uid, question=standalone_question)
    if not ctx:
        answer = generate_chat_response(question)
        add_to_history(uid, question, answer)
        return {"answer": answer, "citations": [], "context": []}

    context_for_prompt = ctx[:8]

    answer = generate_grounded_answer(question=standalone_question, context_blocks=context_for_prompt)
    add_to_history(uid, question, answer)

    citations = [
        {"doc_id": c["doc_id"], "page": c.get("page"), "chunk_id": c["chunk_id"], "score": c.get("score")}
        for c in ctx[:8]
    ]
    return {"answer": answer, "citations": citations, "context": ctx[:8]}

@app.get("/documents")
async def documents(
    user_id: str | None = None,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    uid = _resolve_user_id(x_user_id, user_id)

    drv = get_driver()
    with drv.session() as s:
        res = s.run(
            """
            MATCH (:User {user_id:$user_id})-[:OWNS]->(d:Document {user_id:$user_id})
            RETURN d.doc_id AS doc_id, d.title AS title
            ORDER BY d.title
            """,
            user_id=uid
        )
        return {"documents": [dict(r) for r in res]}
