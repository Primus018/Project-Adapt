# ContractIQ — Contract Clause QA with Corrective RAG

**Topic 1 · Scope: ~50%**  
**Implemented module:** Confidence-gated retrieval evaluator + corrective RAG loop (`ACCEPT` / `RE_RETRIEVE` / `WEB_SEARCH` stub)

Remaining Topic 1 work (Adaptive-RAG routing, live web search, multi-benchmark eval, latency/cost study) is documented as upcoming features — see [`docs/UPCOMING_FEATURES.md`](docs/UPCOMING_FEATURES.md).

## Quick Start

```bash
# Backend (demo mode — no GPU/models required)
cd backend
pip install -r requirements.txt
DEMO_MODE=1 uvicorn main:app --reload --port 8001

# Frontend
cd frontend
npm install && npm run dev
# → http://localhost:5171
```

## Sample upload files

All demo files live in [`samples/`](samples/):

| File | Format | Use |
|------|--------|-----|
| [`samples/sample_msa.txt`](samples/sample_msa.txt) | TXT | Master Services Agreement (recommended) |
| [`samples/sample_msa.pdf`](samples/sample_msa.pdf) | PDF | Same MSA as PDF upload |
| [`samples/sample_nda.txt`](samples/sample_nda.txt) | TXT | NDA with 5-year confidentiality term |

Also mirrored at project root as [`sample_contract.txt`](sample_contract.txt) (same as `sample_msa.txt`).

### Login

Client-side demo auth (any non-empty email/password works):

- Email: `demo@college.edu`
- Password: `demo123`

Session is stored in `localStorage`. Dashboard shows KPIs only; upload + query live on **Corrective QA**.

### Demo steps

1. Open http://localhost:5171 → sign in → land on **Dashboard**.
2. Click **Go to Corrective QA** (upload is not on the dashboard).
3. Upload `samples/sample_msa.txt` (or `.pdf`) and ask:
   - *What is the termination notice period?*
   - *What is the monthly retainer?*
   - *Which law governs this agreement?*
4. Review passage grades (`CORRECT` / `AMBIGUOUS` / `INCORRECT`) and the corrective action grounded in **your uploaded text**.

`DEMO_MODE=1` uses lexical retrieval/grading (no heavy models) but still processes the real document.

**Answer LLM:** optional Ollama **`llama3.1:8b`** when `DEMO_MODE=0`; otherwise extractive (no generative LLM).  
**RAG note:** pipeline works but is not fully efficient — see [`docs/RAG_EFFICIENCY.md`](docs/RAG_EFFICIENCY.md).  
**Status:** [`../IMPLEMENTATION_STATUS.md`](../IMPLEMENTATION_STATUS.md)

## Tests

```bash
cd backend && DEMO_MODE=1 pytest tests -q
```

API check:

```bash
curl -s -F "file=@samples/sample_msa.txt" http://127.0.0.1:8001/api/upload
```

## Stack
- **Backend:** FastAPI + SQLite
- **AI:** Ollama llama3.1:8b (optional) / DeBERTa NLI + BGE / lexical demo
- **Frontend:** React + Vite + Tailwind

## Docs
- [`docs/PROJECT_DOCUMENTATION.md`](docs/PROJECT_DOCUMENTATION.md) — full project explanation
- [`docs/REPORT.md`](docs/REPORT.md) — project report
- [`docs/PRESENTATION.pptx`](docs/PRESENTATION.pptx) — slides
- [`docs/UPCOMING_FEATURES.md`](docs/UPCOMING_FEATURES.md) — future work
- [`docs/RAG_EFFICIENCY.md`](docs/RAG_EFFICIENCY.md) — efficiency limitations
- Root: [`../CODE_WALKTHROUGH.md`](../CODE_WALKTHROUGH.md) · [`../DEPLOYMENT_VERCEL.md`](../DEPLOYMENT_VERCEL.md)

## API
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/upload` | Upload PDF/TXT |
| GET | `/api/documents` | List documents |
| POST | `/api/query` | Corrective RAG query |
| GET | `/api/history` | All queries |
| GET | `/api/stats` | Dashboard KPIs |
| GET | `/api/health` | Health + generator LLM info |
