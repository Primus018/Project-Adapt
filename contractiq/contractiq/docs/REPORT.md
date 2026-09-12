# ContractIQ — Project Report

**Topic 1:** Confidence-Gated Corrective RAG for Domain QA  
**Student:** Raunak Rathi  
**Delivery scope:** ~50% (one core module)  
**Module implemented:** Retrieval-quality evaluator + corrective RAG loop  

---

## 1. Abstract

ContractIQ is a domain QA system for legal/contract documents that grades retrieved passages as CORRECT, AMBIGUOUS, or INCORRECT and triggers corrective actions before answer generation. This delivery implements the confidence-gated corrective loop (ACCEPT / RE_RETRIEVE / WEB_SEARCH stub) with a modern dashboard UI. Adaptive-RAG routing, live web search, and multi-benchmark evaluation are documented as upcoming features.

## 2. Problem Statement

Standard RAG degrades when retrieval returns irrelevant or partially relevant passages, causing unsupported answers. Corrective RAG (CRAG-style) methods assess retrieval quality and recover via re-retrieval or external search, but are under-tested on domain corpora with small open models.

## 3. Objectives (50% cut)

1. Build a modular RAG pipeline with a lightweight retrieval-quality evaluator.
2. Implement corrective actions: ACCEPT, RE_RETRIEVE, and WEB_SEARCH (stubbed for future work).
3. Deliver a usable FastAPI backend and React dashboard for contract upload and QA.
4. Document remaining Topic 1 goals as upcoming features.

**Deferred:** Adaptive-RAG complexity routing, live web search, NQ/HotpotQA evaluation, latency/cost study.

## 4. System Design

```
PDF/TXT → chunk + embed → dense retrieve → grade passages
    → ACCEPT | RE_RETRIEVE | WEB_SEARCH → generate answer → store history
```

| Layer | Technology |
|-------|------------|
| Frontend | React, Vite, Tailwind |
| Backend | FastAPI, SQLite |
| Evaluator | DeBERTa NLI + BGE embeddings (demo lexical fallback) |
| Generator | Ollama llama3.1 (extractive fallback) |

## 5. Implemented Module

**RetrievalEvaluator** (`backend/core.py`) combines NLI entailment scores with semantic similarity to assign grades and choose an action. **ContractQA** runs retrieve → evaluate → correct → generate. Demo mode (`DEMO_MODE=1`) enables demos without GPU/model downloads.

## 6. How to Run

```bash
# Backend (port 8001)
cd contractiq/backend
DEMO_MODE=1 uvicorn main:app --reload --port 8001

# Frontend (port 5171)
cd contractiq/frontend
npm install && npm run dev
```

Upload `sample_contract.txt` and ask: *What is the termination notice period?*

## 7. Results Framing

This phase demonstrates engineering of the corrective loop and UI observability (grades, action, correction rate). Quantitative EM/F1 and faithfulness benchmarks are part of upcoming work.

## 8. Limitations

- WEB_SEARCH does not call an external engine yet.
- Demo mode uses lexical overlap, not NLI.
- Single-document in-memory index (reloaded from SQLite preview on restart).

## 9. Future Work / Upcoming Features

See [UPCOMING_FEATURES.md](UPCOMING_FEATURES.md).

## 10. References

- Yan et al. Corrective Retrieval Augmented Generation (CRAG). arXiv 2024.
- Jeong et al. Adaptive-RAG. NAACL 2024.
- Wang et al. Astute RAG. arXiv 2024.
