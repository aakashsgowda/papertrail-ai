# PaperTrail AI — Knowledge Graph-Powered Document Intelligence

A full-stack Graph RAG (Retrieval-Augmented Generation) application that lets users upload PDFs and ask questions with knowledge graph-powered retrieval. Built with Next.js, FastAPI, Neo4j, and Google Gemini.

## Architecture

```
Browser (Next.js)
    │
    ├─► /upload   ──► PDF Ingestion ──► Neo4j Graph
    │                   ├─ Page extraction (PyPDF)
    │                   ├─ Text chunking (sliding window)
    │                   ├─ Embedding generation (Gemini)
    │                   └─ Entity extraction (LLM)
    │
    └─► /ask      ──► Hybrid Retrieval ──► Grounded Answer
                        ├─ Vector similarity search
                        ├─ Graph expansion via shared entities
                        └─ LLM answer generation with citations
```

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Frontend   | Next.js 16, React 19, Tailwind CSS 4 |
| Backend    | FastAPI, Python 3.11                |
| Database   | Neo4j (graph + vector search)       |
| LLM        | Google Gemini (gemini-2.0-flash)    |
| Embeddings | Gemini (gemini-embedding-001, 3072d)|
| Deployment | Google Cloud Run, Docker            |

## Project Structure

```
papertrail-ai/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env
│   └── app/
│       ├── main.py              # FastAPI endpoints
│       ├── config.py            # Settings (env vars)
│       ├── models.py            # Pydantic models
│       ├── neo4j_db.py          # Neo4j driver
│       ├── schema.py            # DB schema & indexes
│       ├── retrieve.py          # Hybrid retrieval logic
│       └── rag/
│           ├── llm.py           # Gemini: embed, classify, generate, rewrite
│           ├── ingest.py        # PDF ingestion pipeline
│           ├── chunking.py      # Sliding window text chunking
│           ├── entity_extract.py# Named entity extraction
│           └── pdf.py           # PDF page extraction
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── app/
│       │   ├── layout.tsx       # Root layout
│       │   ├── page.tsx         # Chat interface
│       │   └── globals.css      # Global styles
│       └── lib/
│           ├── api.ts           # API client
│           └── user.ts          # Session management
├── clear_all_data.py            # Utility: clear DB data
├── full_reset.py                # Utility: full DB reset
├── reset_vector_index.py        # Utility: reset vector index
└── README.md
```

## Features

- **PDF Upload** - Drag-and-drop or file picker with auto-upload
- **Chat Interface** - Scrollable chat with message history
- **Graph RAG Retrieval** - Vector search + entity-based graph expansion
- **Conversation Memory** - LLM rewrites follow-up questions using chat history (e.g., "Who is Pradeep?" → "What is his experience?" resolves correctly)
- **Smart Greeting Detection** - LLM classifies greetings vs real questions
- **Citations** - Every answer includes source document, page, and chunk references
- **User Isolation** - All data scoped per user via user_id
- **Dark Theme UI** - Modern interface with gradient branding

## Knowledge Graph Schema

```
(:User)-[:OWNS]->(:Document)-[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(:Entity)
```

- **User** - `user_id` (unique)
- **Document** - `doc_id`, `title`, `user_id`
- **Chunk** - `chunk_id`, `text`, `page`, `embedding` (3072d vector)
- **Entity** - `name`, `label`, `user_id` (types: Person, Organization, Location, Product, Concept, etc.)
- **Vector Index** - `chunk_embedding_idx` (cosine similarity)

## Retrieval Strategy

1. Embed the user's question using Gemini
2. Vector search on Chunk nodes (top_k=8)
3. Graph expansion: find entities mentioned by matching chunks, then find other chunks mentioning those same entities (expand_k=12)
4. Merge and deduplicate results
5. Generate a grounded answer using the retrieved context

## Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Neo4j database (cloud or local)
- Google Gemini API key

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Create `backend/.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
NEO4J_URI=neo4j+s://your-neo4j-instance
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
EMBEDDING_MODEL=gemini-embedding-001
GEN_MODEL=gemini-2.0-flash
TOP_K=8
EXPAND_K=12
CHUNK_SIZE=1200
OVERLAP_SIZE=200
EMBED_DIM=3072
```

Run:

```bash
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

Run:

```bash
npm run dev
```

## API Endpoints

| Method | Endpoint     | Description                        |
|--------|--------------|------------------------------------|
| GET    | `/health`    | Health check                       |
| POST   | `/session`   | Create new user session            |
| POST   | `/upload`    | Upload and ingest a PDF            |
| POST   | `/ask`       | Ask a question, get grounded answer|
| GET    | `/documents` | List user's uploaded documents     |

## Deployment (Google Cloud Run)

### Backend

```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/PROJECT_ID/REPO/papertrail-backend ./backend

gcloud run deploy papertrail-backend \
  --image us-central1-docker.pkg.dev/PROJECT_ID/REPO/papertrail-backend \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets GEMINI_API_KEY=gemini_api_key:latest \
  --set-env-vars NEO4J_URI="...",NEO4J_USER="neo4j",NEO4J_PASSWORD="...",EMBEDDING_MODEL="gemini-embedding-001",GEN_MODEL="gemini-2.0-flash",TOP_K=8,EXPAND_K=12,CHUNK_SIZE=1200,OVERLAP_SIZE=200,EMBED_DIM=3072
```

### Frontend

```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/PROJECT_ID/REPO/papertrail-frontend ./frontend

gcloud run deploy papertrail-frontend \
  --image us-central1-docker.pkg.dev/PROJECT_ID/REPO/papertrail-frontend \
  --region us-central1 \
  --allow-unauthenticated
```

> Note: `NEXT_PUBLIC_API_BASE` is baked at build time via the Dockerfile ARG. Update the default in `frontend/Dockerfile` for your backend URL.

## Conversation Memory

The backend maintains per-user conversation history (last 10 turns, in-memory). When a follow-up question comes in:

1. The LLM rewrites it into a standalone question using conversation history
2. The standalone question is used for retrieval
3. This enables natural multi-turn conversations

Example:
- User: "Who is Pradeep?"
- Assistant: "Pradeep is a software engineer who..."
- User: "What is his experience?"
- Rewritten: "What is Pradeep's experience?" → used for retrieval
