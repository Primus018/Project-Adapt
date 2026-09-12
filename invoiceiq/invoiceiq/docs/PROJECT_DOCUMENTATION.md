# InvoiceIQ — Project Documentation

**Product:** Invoice key-field extraction from images and PDFs  
**Folder:** `invoiceiq/`  
**Topic alignment:** Document understanding / OCR KIE (product 50%; **LoRA ≤3B VLM is out of scope**)

---

## 1. What this project does

InvoiceIQ extracts structured business fields from an invoice file:

- Vendor, address, invoice number, dates, bill-to  
- Subtotal, tax, total, currency, payment terms  
- Line items when detectable  

It prefers **real file content** (PDF text or OCR), not canned demo amounts.

## 2. Who it is for

AP automation demos, finance ops, and document-AI showcases on limited hardware.

## 3. Architecture

```
Browser (React, port 5173)
    → /api/extract (multipart file)
FastAPI (port 8003)
    → core.InvoiceExtractor
    → uploads/ + SQLite (extractions)
```

| Layer | Path | Role |
|-------|------|------|
| UI | `frontend/src/App.jsx` | Login, dashboard (no upload), extract workspace, history |
| API helper | `frontend/src/api.js` | `VITE_API_URL` for Vercel |
| API | `backend/main.py` | Extract, list, stats; PDF → first-page image |
| Core | `backend/core.py` | PDF text → VLM → OCR → parse fields |
| Samples | `samples/` | PNG/JPG/PDF demo invoices |

## 4. Extraction pipeline (order)

1. **PDF native text** (PyMuPDF) when selectable text exists  
2. **Ollama vision** (`llava:7b`) if installed  
3. **Tesseract OCR** on images (`brew install tesseract`)  
4. Regex / heuristics to map text → fields  
5. Fallback message only if nothing readable (does **not** invent fake Acme totals as success)

## 5. User flow

1. Login.  
2. Dashboard — stats only.  
3. **Extract Invoice** — upload PNG/JPG/PDF.  
4. Review fields, confidence, line items.  
5. History / Upcoming (product roadmap — no LoRA training).

## 6. Models

| Path | Model / tool |
|------|----------------|
| Default college demo | Tesseract OCR + regex / PDF text |
| Optional | Ollama `llava:7b` |
| Out of scope | LoRA fine-tune of ≤3B VLMs |

## 7. Implemented vs pending

**Implemented:** single-page/image KIE, OCR/PDF path, UI, samples, tests.  
**Pending:** multi-page merge, human edit + CSV export, stronger table parsing, confidence calibration.  
**Not planned:** LoRA / QLoRA VLM training as a delivery objective.

## 8. Local run

```bash
# OCR recommended for images
brew install tesseract

cd invoiceiq/backend
pip install -r requirements.txt
DEMO_MODE=1 uvicorn main:app --reload --port 8003

cd ../frontend
npm install && npm run dev
# http://127.0.0.1:5173
```

Try `samples/sample_invoice_text.pdf` (best) or `samples/sample_invoice.png`.

## 9. Tests

```bash
cd invoiceiq/backend
DEMO_MODE=1 pytest tests -q
```

## 10. Related docs

| File | Purpose |
|------|---------|
| `README.md` | Quick start |
| `docs/PROJECT_DOCUMENTATION.md` | This file |
| `docs/REPORT.md` | Report |
| `docs/UPCOMING_FEATURES.md` | Product roadmap |
| `docs/PRESENTATION.pptx` | Slides |
