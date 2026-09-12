# InvoiceIQ — Project Report

**Topic 9:** Compact VLMs for Document Understanding  
**Student:** Raunak Rathi  
**Delivery scope:** ~50% (one core module)  
**Module implemented:** Invoice key-information extraction pipeline  

---

## 1. Abstract

InvoiceIQ extracts structured fields (vendor, dates, totals, line items) from invoice images/PDFs using PDF text extraction and OCR (Tesseract), with an optional Ollama vision model when installed. **LoRA fine-tuning of ≤3B VLMs is not an objective** for this project.

## 2. Problem Statement

Multimodal document understanding is dominated by large VLMs. Compact models that run on limited hardware for invoices and forms are needed for on-premise and low-cost deployment. Key-information extraction is a practical first module toward that goal.

## 3. Objectives (50% cut)

1. Implement an invoice field extraction pipeline (VLM → OCR → demo fallback).
2. Persist extractions and expose stats via FastAPI.
3. Deliver a React dashboard for upload, field review, and history.
4. Document remaining Topic 9 goals as upcoming features.

**Deferred (product):** multi-page merge, human correction/export, stronger table parsing, confidence calibration.  
**Out of scope:** LoRA on small VLMs; full OCRBench research suite as a hard requirement.

## 4. System Design

```
image/PDF → (optional PDF rasterize) → Ollama VLM | Florence-2 | Tesseract | demo
    → structured fields + line items → SQLite
```

| Layer | Technology |
|-------|------------|
| Frontend | React, Vite, Tailwind |
| Backend | FastAPI, SQLite, Pillow, PyMuPDF |
| Models | Ollama llava / Florence-2 / pytesseract (demo fallback) |

## 5. Implemented Module

**InvoiceExtractor** (`backend/core.py`) attempts vision-model JSON extraction, then Florence OCR parsing, then Tesseract regex parsing, then a deterministic demo schema so the UI always works.

## 6. How to Run

```bash
cd invoiceiq/backend
DEMO_MODE=1 uvicorn main:app --reload --port 8003

cd invoiceiq/frontend
npm install && npm run dev
```

Upload any PNG/JPG/PDF invoice; demo mode returns realistic structured fields.

## 7. Results Framing

This phase demonstrates an end-to-end KIE product path using OCR/PDF text. Formal public-benchmark campaigns are optional research extensions, not LoRA training objectives.

## 8. Limitations

- Demo fields are synthesized when models are unavailable.
- Single-page focus (first PDF page only).
- No trained domain adapter yet.

## 9. Future Work / Upcoming Features

See [UPCOMING_FEATURES.md](UPCOMING_FEATURES.md).

## 10. References

- DocSLM. arXiv 2025.
- Fu et al. OCRBench v2. arXiv 2025.
- Hu et al. mPLUG-DocOwl2. arXiv 2024.
- Poznanski et al. olmOCR. arXiv 2025.
