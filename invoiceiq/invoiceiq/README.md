# InvoiceIQ — Invoice Data Extractor with Small VLM

**Topic 9 · Invoice key-field extraction**  
**Implemented module:** Invoice OCR/PDF field extraction (vendor, dates, totals, line items)

**Out of scope:** LoRA fine-tune of ≤3B VLMs (not an objective for this delivery).

Product upcoming work — see [`docs/UPCOMING_FEATURES.md`](docs/UPCOMING_FEATURES.md).  
Full implemented vs pending matrix: [`../IMPLEMENTATION_STATUS.md`](../IMPLEMENTATION_STATUS.md).

## Quick Start

```bash
# Backend (demo mode — no VLM required)
cd backend
pip install -r requirements.txt
DEMO_MODE=1 uvicorn main:app --reload --port 8003

# Frontend
cd frontend
npm install && npm run dev
# → http://localhost:5173
```

## Sample upload files

Demo invoices are in [`samples/`](samples/):

| File | Format | Use |
|------|--------|-----|
| [`samples/sample_invoice.png`](samples/sample_invoice.png) | PNG | Recommended image upload (OCR) |
| [`samples/sample_invoice.jpg`](samples/sample_invoice.jpg) | JPG | Same invoice as JPEG |
| [`samples/sample_invoice.pdf`](samples/sample_invoice.pdf) | PDF | Image-based PDF (OCR after rasterize) |
| [`samples/sample_invoice_text.pdf`](samples/sample_invoice_text.pdf) | PDF | Text-layer PDF (best accuracy, no OCR) |

The sample includes vendor **Acme Cloud Labs Pvt Ltd**, invoice **INV-48291**, line items, GST, and total **₹23,010.00**.

### Requirements for real extraction

InvoiceIQ now reads **your uploaded file content** (not fake demo values):

1. **Text PDFs** → extracted with PyMuPDF  
2. **Images / scanned PDFs** → Tesseract OCR (`brew install tesseract`)  
3. Optional: Ollama vision model (`llava`) if installed  

If OCR is missing and the file has no selectable text, the UI shows a fallback message instead of invented amounts.

### Login

Client-side demo auth (any non-empty email/password works):

- Email: `demo@college.edu`
- Password: `demo123`

Dashboard is KPIs only; upload lives on **Extract Invoice**.

### Demo steps

1. Open http://localhost:5173 → sign in → **Dashboard** → **Extract Invoice**.
2. Click **Upload invoice** on the workspace (not the dashboard).
3. Prefer `samples/sample_invoice_text.pdf` (text layer) or `samples/sample_invoice.png` (needs Tesseract).
4. Confirm vendor, invoice number (`INV-48291`), dates, tax, and total match the file.
5. Upload a different invoice — fields should change with the document (no invented Acme amounts).

OCR dependency for scanned images:

```bash
brew install tesseract
```

API check:

```bash
curl -s -F "file=@samples/sample_invoice.png" http://127.0.0.1:8003/api/extract
curl -s -F "file=@samples/sample_invoice_text.pdf" http://127.0.0.1:8003/api/extract
```

**Models:** Optional Ollama `llava:7b` (vision); default path is **Tesseract OCR + regex** / PDF text. No LoRA training.

Full status: [`../IMPLEMENTATION_STATUS.md`](../IMPLEMENTATION_STATUS.md).

## Stack
- **Backend:** FastAPI + SQLite + Pillow + PyMuPDF
- **AI:** Ollama llava (optional) / Tesseract OCR / PDF text
- **Frontend:** React + Vite + Tailwind

## Tests

```bash
cd backend
DEMO_MODE=1 pytest tests -q
```

## Docs
- [`docs/PROJECT_DOCUMENTATION.md`](docs/PROJECT_DOCUMENTATION.md) — full project explanation
- [`docs/REPORT.md`](docs/REPORT.md) — project report
- [`docs/PRESENTATION.pptx`](docs/PRESENTATION.pptx) — slides
- [`docs/UPCOMING_FEATURES.md`](docs/UPCOMING_FEATURES.md) — future work (no LoRA)
- Root: [`../CODE_WALKTHROUGH.md`](../CODE_WALKTHROUGH.md) · [`../DEPLOYMENT_VERCEL.md`](../DEPLOYMENT_VERCEL.md)

## API
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/extract` | Extract invoice fields |
| GET | `/api/extractions` | List extractions |
| GET | `/api/stats` | Dashboard KPIs |
| GET | `/api/health` | Health + scope |
