# PaperTrail AI — Project State

**Last updated:** 2026-04-27  
**Branch:** main  
**Remote:** https://github.com/aakashsgowda/papertrail-ai.git

---

## Completed Phases

### Phase 1 — Cleanup & Rebrand
- Rebranded from DocSage → PaperTrail AI (UI, README, prompts)
- Fixed context cap bug: `max(8, len(ctx))` → `ctx[:8]`
- Added `try/finally` temp-file cleanup in `main.py`
- Removed dead `AskRequest` / `AskResponse` models
- Extended `.gitignore`

### Phase 2 — Paper Metadata Extraction
- `backend/app/rag/metadata_extract.py` — new file
- `extract_paper_metadata()` — Gemini LLM extracts title, authors, abstract, section headings from first two PDF pages
- `PaperMetadata` Pydantic model added to `models.py`
- `UploadResponse` extended to return metadata
- `ingest_pdf()` return type changed to `tuple[str, dict]`

### Phase 3 — ML-Specific Entity Extraction
- `backend/app/rag/entity_extract.py` — complete rewrite
- Taxonomy: `MLModel`, `Dataset`, `Metric`, `Task`, `Method`, `Framework`, `Benchmark`, `Finding`, `Other`
- `_VALID_TYPES` allowlist enforcement
- `_MAX_NAME_LEN = 120` guard with truncation
- Deduplication via lowercase key set
- Cap at 8 entities per chunk

### Phase 4A — Section-Aware Retrieval
- `assign_chunk_sections()` in `metadata_extract.py` — assigns canonical section label to each chunk via page-level regex
- Canonical labels: `abstract`, `introduction`, `method`, `experiments`, `results`, `discussion`, `limitations`, `conclusion`, `background`, `unknown`
- `classify_question_intent()` in `llm.py` — classifies question into `method / results / background / limitations / general`
- `retrieve_with_graph()` applies `+0.15` score boost to chunks in matching sections, then re-sorts
- Section index added to Neo4j schema: `chunk_section_idx`

### Phase 4B — Graph Retrieval Fixes
- Vector search over-fetches by `VECTOR_FETCH_MULTIPLIER` (default 5), filters by `user_id`, then caps at `TOP_K`
- Entity degree guard in graph expansion: skips entities with degree > `MAX_ENTITY_DEGREE` (default 50)
- `vector_fetch_multiplier` and `max_entity_degree` added to `config.py`

---

## Current Status

| Layer | Status |
|---|---|
| Backend code | Complete |
| Neo4j schema | Initialized on startup |
| Neo4j AuraDB connection | SSL fixed (ran `Install Certificates.command`); auth troubleshooting in progress |
| Frontend | Not yet tested locally |
| End-to-end test | Pending |

### Known Blocker
Neo4j AuraDB `AuthError` — password in `backend/.env` needs to be updated from the AuraDB console → three-dot menu → **Recover database credentials**.

---

## Pending Work

- [ ] Fix Neo4j auth (`NEO4J_PASSWORD` in `.env`)
- [ ] Start backend: `uvicorn app.main:app --reload --port 8000`
- [ ] Frontend setup: `cd frontend && npm install`, create `frontend/.env.local`, run `npm run dev`
- [ ] End-to-end test: upload a PDF, ask a question, verify citations
- [ ] Phase 5 (planned): persistent conversation history, batched embeddings, document management UI

---

## Local Setup Quick Reference

```bash
# Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/docs

# Frontend
cd frontend
npm install
# create frontend/.env.local with: NEXT_PUBLIC_API_BASE=http://localhost:8000
npm run dev
# → http://localhost:3000
```

---

## Key Files

| File | Purpose |
|---|---|
| `backend/app/main.py` | FastAPI entry point, upload + query routes |
| `backend/app/rag/ingest.py` | Full ingestion pipeline |
| `backend/app/rag/metadata_extract.py` | Paper metadata + section assignment |
| `backend/app/rag/entity_extract.py` | ML entity extraction |
| `backend/app/rag/llm.py` | All Gemini calls (embed, generate, classify) |
| `backend/app/retrieve.py` | Vector search + graph expansion + section re-rank |
| `backend/app/schema.py` | Neo4j constraints + indexes |
| `backend/app/config.py` | All env var settings |
| `frontend/src/app/page.tsx` | Main chat UI |
