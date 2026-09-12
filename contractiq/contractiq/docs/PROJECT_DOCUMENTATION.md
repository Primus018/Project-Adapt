# ContractIQ — Project Documentation

**Product:** Contract clause QA with confidence-gated corrective RAG  
**Folder:** `contractiq/`  
**Topic alignment:** Corrective / Adaptive RAG for domain QA (50% delivery)

---

## 1. What this project does

ContractIQ lets a user upload a legal/contract PDF or TXT file, ask natural-language questions, and receive answers grounded in retrieved clauses. Before answering, the system **grades** retrieved passages as CORRECT / AMBIGUOUS / INCORRECT and may **re-retrieve** if quality is weak.

## 2. Who it is for

Legal ops, contract analysts, and research demos that need observable retrieval quality (grades + corrective action), not a black-box chatbot.

## 3. Architecture

```
Browser (React, port 5171)
    → /api/* (Vite proxy locally, or VITE_API_URL in production)
FastAPI (port 8001)
    → core.ContractQA + RetrievalEvaluator
    → SQLite (documents, queries)
```

| Layer | Path | Role |
|-------|------|------|
| UI | `frontend/src/App.jsx` | Login, dashboard, Corrective QA, history, upcoming |
| API helper | `frontend/src/api.js` | `VITE_API_URL` + path join |
| API | `backend/main.py` | Upload, query, stats, history |
| Core | `backend/core.py` | Chunk, retrieve, grade, correct, generate |
| Samples | `samples/` | MSA / NDA demo files |

## 4. User flow

1. Login (`demo@college.edu` / `demo123` or any non-empty pair).
2. **Dashboard** — KPIs only (no upload).
3. **Corrective QA** — upload contract, ask question.
4. UI shows answer, corrective action (`ACCEPT` / `RE_RETRIEVE` / `WEB_SEARCH`), and passage grades.
5. **History** / **Upcoming**.

## 5. Backend behavior

### Upload (`POST /api/upload`)
- Accepts `.pdf` / `.txt`
- PDF text via PyMuPDF
- Chunks + embeds (or lexical tokens in `DEMO_MODE=1`)
- Stores full text in SQLite

### Query (`POST /api/query`)
1. Reload selected document into memory if needed  
2. Retrieve top-k passages  
3. Grade each passage  
4. Corrective action  
5. Generate answer  
6. Persist query row  

### Models / LLM

| Mode | Generator | Retriever / grader |
|------|-----------|--------------------|
| `DEMO_MODE=1` | **No LLM** — extractive sentence pick | Lexical overlap |
| `DEMO_MODE=0` + Ollama | **`llama3.1:8b`** | BGE embeddings + DeBERTa NLI |

RAG **works** but is not fully efficient yet — see `docs/RAG_EFFICIENCY.md`.

## 6. Implemented vs pending

**Implemented:** confidence-gated evaluator, ACCEPT/RE_RETRIEVE, WEB_SEARCH stub, UI, samples, tests.  
**Pending:** Adaptive-RAG routing, live web search, ANN/FAISS efficiency, public QA benchmarks.

## 7. Local run

```bash
cd contractiq/backend
pip install -r requirements.txt
DEMO_MODE=1 uvicorn main:app --reload --port 8001

cd ../frontend
npm install && npm run dev
# http://127.0.0.1:5171
```

## 8. Tests

```bash
cd contractiq/backend
DEMO_MODE=1 pytest tests -q
```

## 9. Related docs in this folder

| File | Purpose |
|------|---------|
| `README.md` | Quick start |
| `docs/PROJECT_DOCUMENTATION.md` | This file |
| `docs/REPORT.md` | Academic-style report |
| `docs/RAG_EFFICIENCY.md` | Efficiency notes |
| `docs/UPCOMING_FEATURES.md` | Roadmap |
| `docs/PRESENTATION.pptx` | Slides |
