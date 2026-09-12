"""InvoiceIQ — FastAPI Backend"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="InvoiceIQ", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = "database/invoiceiq.db"
UPLOADS = "uploads"


def init_db():
    os.makedirs("database", exist_ok=True)
    os.makedirs(UPLOADS, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS extractions (
            id TEXT PRIMARY KEY, filename TEXT, doc_type TEXT,
            total_amount REAL, field_count INTEGER,
            line_item_count INTEGER, fields TEXT,
            line_items TEXT, created_at TEXT
        );
        """
    )
    conn.close()


init_db()

extractor = None


def get_extractor():
    global extractor
    if extractor is None:
        from core import InvoiceExtractor

        extractor = InvoiceExtractor()
    return extractor


class FieldResponse(BaseModel):
    field_name: str
    value: str
    confidence: float
    category: str


class ExtractionResponse(BaseModel):
    id: str
    filename: str
    document_type: str
    fields: List[FieldResponse]
    line_items: list
    total_amount: Optional[float]
    mode: str = "live"


@app.post("/api/extract", response_model=ExtractionResponse)
async def extract_invoice(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".pdf", ".tiff")):
        raise HTTPException(400, "Supported: PNG, JPG, PDF, TIFF")

    eid = str(uuid.uuid4())[:8]
    path = os.path.join(UPLOADS, f"{eid}_{file.filename}")
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    work_path = path
    pdf_path = None
    if file.filename.lower().endswith(".pdf"):
        pdf_path = path
        try:
            import fitz

            doc = fitz.open(path)
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2))
            img_path = os.path.join(UPLOADS, f"{eid}_page0.png")
            pix.save(img_path)
            work_path = img_path
        except Exception:  # noqa: BLE001
            work_path = path

    ext = get_extractor()
    result = ext.extract(work_path, pdf_path=pdf_path)

    fields_data = [
        {
            "field_name": f.field_name,
            "value": f.value,
            "confidence": f.confidence,
            "category": f.category,
        }
        for f in result.fields
    ]

    conn = sqlite3.connect(DB)
    conn.execute(
        "INSERT INTO extractions VALUES (?,?,?,?,?,?,?,?,?)",
        (
            eid,
            file.filename,
            result.document_type,
            result.total_amount,
            len(result.fields),
            len(result.line_items),
            json.dumps(fields_data),
            json.dumps(result.line_items),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    return ExtractionResponse(
        id=eid,
        filename=file.filename,
        document_type=result.document_type,
        fields=fields_data,
        line_items=result.line_items,
        total_amount=result.total_amount,
        mode=getattr(result, "mode", "live"),
    )


@app.get("/api/extractions")
async def list_extractions():
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, filename, doc_type, total_amount, field_count, line_item_count, created_at FROM extractions ORDER BY created_at DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "filename": r[1],
            "doc_type": r[2],
            "total_amount": r[3],
            "field_count": r[4],
            "line_item_count": r[5],
            "created_at": r[6],
        }
        for r in rows
    ]


@app.get("/api/extraction/{eid}")
async def get_extraction(eid: str):
    conn = sqlite3.connect(DB)
    row = conn.execute("SELECT * FROM extractions WHERE id=?", (eid,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Extraction not found")
    return {
        "id": row[0],
        "filename": row[1],
        "doc_type": row[2],
        "total_amount": row[3],
        "fields": json.loads(row[6]),
        "line_items": json.loads(row[7]),
        "created_at": row[8],
    }


@app.get("/api/stats")
async def get_stats():
    conn = sqlite3.connect(DB)
    total = conn.execute("SELECT COUNT(*) FROM extractions").fetchone()[0]
    avg_fields = conn.execute(
        "SELECT AVG(field_count) FROM extractions"
    ).fetchone()[0]
    sum_amount = conn.execute(
        "SELECT SUM(total_amount) FROM extractions"
    ).fetchone()[0]
    by_type = conn.execute(
        "SELECT doc_type, COUNT(*) FROM extractions GROUP BY doc_type"
    ).fetchall()
    recent = conn.execute(
        "SELECT id, filename, doc_type, total_amount, created_at FROM extractions ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    conn.close()

    return {
        "extractions": total,
        "avg_fields": round(avg_fields or 0, 1),
        "total_amount_sum": round(sum_amount or 0, 2),
        "by_type": {t: c for t, c in by_type},
        "model_loaded": extractor is not None,
        "demo_mode": bool(getattr(extractor, "demo", True))
        if extractor
        else os.getenv("DEMO_MODE", "0") == "1",
        "recent": [
            {
                "id": r[0],
                "filename": r[1],
                "doc_type": r[2],
                "total_amount": r[3],
                "created_at": r[4],
            }
            for r in recent
        ],
    }


@app.get("/api/health")
async def health():
    ext = extractor
    return {
        "status": "ok",
        "extractor_loaded": extractor is not None,
        "demo_mode": os.getenv("DEMO_MODE", "0") == "1",
        "tesseract_ok": bool(getattr(ext, "tesseract_ok", False)) if ext else False,
        "module": "invoice-key-field-extraction",
    }
