# PaperTrail AI

**Graph-powered intelligence for research papers.**

Upload PDFs. Ask questions. Get answers grounded in a knowledge graph built from your documents — with citations, section-aware ranking, and entity-level connections across papers.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![Next.js](https://img.shields.io/badge/Next.js-16-black)
![Neo4j](https://img.shields.io/badge/Neo4j-Graph%20%2B%20Vector-teal)
![Gemini](https://img.shields.io/badge/Google-Gemini-orange)

---

> **Screenshot / Demo GIF**
> `[ placeholder — add a screen recording or screenshot of the chat interface here ]`

---

## Overview

PaperTrail AI is a full-stack Retrieval-Augmented Generation (RAG) system designed specifically for machine learning and NLP research papers.

Standard RAG treats documents as flat bags of text chunks. PaperTrail AI builds a **knowledge graph** on top of your PDFs — extracting paper metadata, named ML entities, and section structure — then uses that graph to retrieve richer, more targeted context when you ask a question.

The system is built for:
- Researchers who need to query across multiple papers simultaneously
- Engineers exploring a new ML subfield and asking comparative questions
- Anyone who wants document Q&A that understands paper structure, not just keyword overlap

---

## Key Features

- **Graph RAG retrieval** — vector similarity search followed by entity-based graph expansion: chunks that share named entities (models, datasets, metrics) are surfaced even if they aren't semantically close in embedding space
- **Section-aware ranking** — questions about methods boost method/experiments chunks; questions about results boost results/discussion chunks — the LLM always sees the most structurally relevant context
- **ML-specific entity extraction** — extracts `MLModel`, `Dataset`, `Metric`, `Task`, `Method`, `Framework`, `Benchmark`, and `Finding` entities from each chunk and stores them as graph nodes
- **Research paper metadata extraction** — automatically extracts title, authors, abstract, and section headings from each uploaded PDF
- **Multi-turn conversation** — follow-up questions are rewritten into standalone queries using the last 5 turns of conversation history
- **Grounded answers with citations** — every answer includes doc ID, page number, and chunk reference
- **User isolation** — all graph data is scoped per user; one user's documents are never visible to another

---

## Architecture

```
 INGESTION PIPELINE
 ───────────────────────────────────────────────────────────
 PDF file
   │
   ├─► extract_pdf_pages()        pypdf — per-page text
   ├─► extract_paper_metadata()   Gemini — title, authors, abstract, section headings
   ├─► assign_chunk_sections()    regex — canonical section label per chunk
   ├─► chunk_text()               sliding window — 1200 chars, 200 overlap
   ├─► embed_texts()              Gemini text-embedding-004 — 768-dim vectors
   ├─► extract_entities_from_chunk()  Gemini — MLModel, Dataset, Metric, Task, …
   │
   └─► Neo4j
         (:User)-[:OWNS]->(:Document)-[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(:Entity)
         Chunk stores: text, embedding, page, section
         Document stores: paper_title, authors, abstract, section_headings


 QUERY PIPELINE
 ───────────────────────────────────────────────────────────
 User question
   │
   ├─► classify_question()        Gemini — greeting or real question?
   ├─► rewrite_query()            Gemini — resolve follow-up using history
   ├─► embed_texts()              Gemini — embed the (rewritten) question
   │
   ├─► Neo4j vector search        ANN over chunk_embedding_idx (cosine)
   │     over-fetches k×5 candidates, filters by user_id, returns top-k
   │
   ├─► Neo4j graph expansion      Chunk → Entity → other Chunks
   │     skips high-degree entities (configurable threshold)
   │
   ├─► classify_question_intent() Gemini — method / results / background / …
   ├─► section score boost        +0.15 to chunks in matching sections
   ├─► re-rank merged results
   │
   └─► generate_grounded_answer() Gemini — answer from top-8 chunks only
         returns: answer + citations + context
```

---

## How It Works

### Ingestion

1. **PDF upload** — the frontend sends the file to `POST /upload`; the backend writes it to a temp file (deleted after ingestion)
2. **Text extraction** — `pypdf` extracts raw text per page
3. **Paper metadata** — one Gemini call on the first two pages extracts title, authors, and abstract as JSON; a regex scan across all pages detects section headings
4. **Section assignment** — each page is matched to a canonical section label (`abstract`, `introduction`, `method`, `experiments`, `results`, `discussion`, `limitations`, `conclusion`, `background`, `unknown`); every chunk on that page inherits the label
5. **Chunking** — sliding-window character chunker (1200-char chunks, 200-char overlap) runs per page
6. **Embedding** — each chunk is embedded with Gemini `text-embedding-004` (768 dimensions)
7. **Neo4j write** — `User`, `Document`, and `Chunk` nodes are created with all properties; a vector index (`chunk_embedding_idx`, cosine) is maintained on `Chunk.embedding`
8. **Entity extraction** — one Gemini call per chunk extracts up to 8 ML-specific entities; `Entity` nodes are merged (deduplicated by user + name) and linked via `MENTIONS` edges

### Querying

1. **Classification** — a fast Gemini call classifies the question as a greeting or a real document question; greetings bypass retrieval entirely
2. **Query rewriting** — follow-up questions are rewritten into standalone questions using the last 5 conversation turns
3. **Vector search** — the question is embedded; Neo4j's ANN index returns the top `k × VECTOR_FETCH_MULTIPLIER` candidates globally, filtered by `user_id`, capped at `TOP_K`
4. **Graph expansion** — for each retrieved chunk, the graph is traversed to find other chunks sharing the same entities; high-degree entities (degree > `MAX_ENTITY_DEGREE`) are skipped to avoid noisy stop-word-like traversals
5. **Section-aware re-ranking** — the question's intent (method / results / background / limitations / general) is classified; chunks in matching sections receive a +0.15 score boost; the merged list is re-sorted
6. **Answer generation** — the top 8 chunks are injected into a grounded-answer prompt; Gemini is instructed to answer using only the provided context

---

## What Makes It Different from Standard RAG

| Capability | Standard RAG | PaperTrail AI |
|---|---|---|
| Retrieval mechanism | Vector similarity only | Vector search + knowledge graph expansion |
| Document understanding | Flat text chunks | Extracts title, authors, abstract, section structure |
| Entity awareness | None | ML-specific: MLModel, Dataset, Metric, Task, Method, Framework, Benchmark, Finding |
| Cross-chunk connections | None | Chunks sharing named entities are linked in the graph |
| Query handling | Static retrieval | Intent classification → section-aware boost → re-ranking |
| Multi-turn support | Typically stateless | Follow-up questions rewritten using conversation history |
| User isolation | Often missing | All Neo4j data scoped per user_id |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS 4 |
| Backend | FastAPI, Python 3.11 |
| Graph database | Neo4j (graph storage + ANN vector index) |
| LLM | Google Gemini (`gemini-2.0-flash` or configurable) |
| Embeddings | Google Gemini (`text-embedding-004`, 768 dims) |
| PDF parsing | pypdf |
| Deployment | Docker, Google Cloud Run |

---

## Example Questions

These are the kinds of questions PaperTrail AI is built to answer well across one or more uploaded papers:

**Method questions**
- *"What fine-tuning approach did they use, and why did they choose it?"*
- *"How was the training data preprocessed?"*

**Results questions**
- *"What BLEU score did the model achieve on WMT14?"*
- *"How does their approach compare to the GPT-3 baseline?"*

**Cross-paper questions** *(with multiple PDFs uploaded)*
- *"Which papers use LoRA, and what tasks do they apply it to?"*
- *"Which dataset appears most frequently across the papers I uploaded?"*

**Background questions**
- *"What prior work do the authors cite for attention mechanisms?"*

**Limitations**
- *"What do the authors identify as the main weaknesses of their approach?"*

---

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- A running Neo4j instance (Neo4j AuraDB free tier works)
- A Google Gemini API key

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Create `backend/.env` (see [Environment Variables](#environment-variables) below):

```bash
cp backend/.env.example backend/.env
# fill in your values
```

Start the server:

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

Start the dev server:

```bash
npm run dev
```

The UI will be available at `http://localhost:3000`.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes* | — | Google Gemini API key |
| `NEO4J_URI` | Yes | — | Neo4j connection URI (e.g. `neo4j+s://...`) |
| `NEO4J_USER` | Yes | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | Yes | — | Neo4j password |
| `EMBEDDING_MODEL` | No | `text-embedding-004` | Gemini embedding model |
| `GEN_MODEL` | No | `gemini-1.5-flash` | Gemini generation model |
| `EMBED_DIM` | No | `768` | Embedding dimension (must match model) |
| `TOP_K` | No | `8` | Number of chunks returned by vector search |
| `EXPAND_K` | No | `12` | Max graph-expanded chunks added per query |
| `VECTOR_FETCH_MULTIPLIER` | No | `5` | ANN over-fetch factor for user isolation fix |
| `MAX_ENTITY_DEGREE` | No | `50` | Skip entities connected to more than this many chunks |
| `CHUNK_SIZE` | No | `1200` | Characters per chunk |
| `CHUNK_OVERLAP` | No | `200` | Overlap between consecutive chunks |
| `GOOGLE_GENAI_USE_VERTEX_AI` | No | `False` | Set `True` to use Vertex AI instead of API key |
| `GOOGLE_CLOUD_PROJECT` | No* | — | GCP project ID (required if using Vertex AI) |
| `GOOGLE_CLOUD_REGION` | No* | — | GCP region (required if using Vertex AI) |

\* Either `GEMINI_API_KEY` or Vertex AI credentials must be provided.

### Frontend (`frontend/.env.local`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_BASE` | Yes | — | Full URL of the backend API |

---

## Docker

Both services have production-ready Dockerfiles.

### Backend

```bash
docker build -t papertrail-backend ./backend
docker run -p 8000:8080 --env-file backend/.env papertrail-backend
```

### Frontend

`NEXT_PUBLIC_API_BASE` is baked into the Next.js build at compile time via a Docker `ARG`. You must pass it at build time:

```bash
docker build \
  --build-arg NEXT_PUBLIC_API_BASE=https://your-backend-url.run.app \
  -t papertrail-frontend \
  ./frontend

docker run -p 3000:8080 papertrail-frontend
```

> **Note:** If you change the backend URL after building the frontend image, you must rebuild the frontend image. This is a Next.js static-export constraint, not a PaperTrail AI limitation.

---

## Deployment

> `[ placeholder — deployment instructions for your target platform ]`

The project is structured for Google Cloud Run. Rough outline:

```bash
# Build and push backend
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/PROJECT_ID/REPO/papertrail-backend \
  ./backend

# Deploy backend
gcloud run deploy papertrail-backend \
  --image us-central1-docker.pkg.dev/PROJECT_ID/REPO/papertrail-backend \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets GEMINI_API_KEY=gemini_api_key:latest \
  --set-env-vars NEO4J_URI="...",NEO4J_USER="neo4j",NEO4J_PASSWORD="..."

# Build and push frontend (bake in the deployed backend URL)
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/PROJECT_ID/REPO/papertrail-frontend \
  --build-arg NEXT_PUBLIC_API_BASE=https://papertrail-backend-xxxx.run.app \
  ./frontend

# Deploy frontend
gcloud run deploy papertrail-frontend \
  --image us-central1-docker.pkg.dev/PROJECT_ID/REPO/papertrail-frontend \
  --region us-central1 \
  --allow-unauthenticated
```

A `docker-compose.yml` for local full-stack testing is planned (see [Future Improvements](#future-improvements)).

---

## Future Improvements

These are known gaps or planned additions, roughly in priority order:

- **Authentication** — the current user isolation model trusts the `user_id` sent by the client; a real auth layer (JWT, OAuth) is needed before any public deployment
- **Background ingestion jobs** — PDF ingestion currently blocks the HTTP request; large documents should be processed asynchronously via a job queue (Celery, Cloud Tasks)
- **Batched embedding calls** — embeddings are currently generated one chunk at a time; batching would significantly reduce ingestion time
- **Per-user vector index** — Neo4j Community Edition does not support filtered ANN indexes; the current over-fetch workaround is good enough for small deployments but a dedicated index per user (or Neo4j Enterprise) would be more robust at scale
- **Persistent conversation history** — conversation history is currently stored in-process memory; it should be moved to Redis or a database to survive restarts and support multi-worker deployments
- **Document management UI** — the backend has a `GET /documents` endpoint that lists uploaded documents; the frontend does not yet expose this
- **`docker-compose.yml`** — a compose file for running the full stack locally without manual setup
- **Section-aware ingestion for non-standard papers** — the current section detector uses a known-heading vocabulary; papers that use non-standard headings may not be detected correctly

---

## Acknowledgements

Built on top of:
- [FastAPI](https://fastapi.tiangolo.com/) — async Python web framework
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/) — graph database client
- [Google Generative AI Python SDK](https://github.com/google-gemini/generative-ai-python) — Gemini embeddings and generation
- [pypdf](https://github.com/py-pdf/pypdf) — PDF text extraction
- [Next.js](https://nextjs.org/) — React framework for the frontend
- [Tailwind CSS](https://tailwindcss.com/) — utility-first CSS

The Graph RAG pattern (combining vector similarity with knowledge graph traversal) draws on ideas from Microsoft's GraphRAG research and the broader graph-augmented retrieval literature.
