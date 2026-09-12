"""ContractIQ — FastAPI Backend"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

import fitz  # PyMuPDF
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="ContractIQ", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = "database/contractiq.db"


def init_db():
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY, name TEXT, text TEXT,
            chunks INTEGER, uploaded_at TEXT
        );
        CREATE TABLE IF NOT EXISTS queries (
            id TEXT PRIMARY KEY, doc_id TEXT, question TEXT,
            answer TEXT, action TEXT, was_corrected INTEGER,
            grades TEXT, created_at TEXT,
            FOREIGN KEY(doc_id) REFERENCES documents(id)
        );
        """
    )
    conn.close()


init_db()

qa_engine = None
# Tracks which document text is currently ingested in memory
active_doc_id = None


def get_engine():
    global qa_engine
    if qa_engine is None:
        from core import ContractQA

        qa_engine = ContractQA()
    return qa_engine


def load_document_into_engine(doc_id: str) -> None:
    """Always ingest the requested document's full text (real upload content)."""
    global active_doc_id
    conn = sqlite3.connect(DB)
    row = conn.execute("SELECT text FROM documents WHERE id=?", (doc_id,)).fetchone()
    conn.close()
    if not row or not (row[0] or "").strip():
        raise HTTPException(400, "No document loaded. Upload a document first.")
    engine = get_engine()
    engine.ingest_document(row[0])
    active_doc_id = doc_id


class QueryRequest(BaseModel):
    doc_id: str
    question: str


class QueryResponse(BaseModel):
    id: str
    question: str
    answer: str
    action: str
    was_corrected: bool
    grades: list
    passages_used: int
    mode: str = "live"


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith((".pdf", ".txt")):
        raise HTTPException(400, "Only PDF and TXT files are supported")

    content = await file.read()
    if file.filename.endswith(".pdf"):
        doc = fitz.open(stream=content, filetype="pdf")
        text = "\n\n".join(page.get_text() for page in doc)
    else:
        text = content.decode("utf-8")

    if not text.strip():
        raise HTTPException(400, "Could not extract text from document")

    engine = get_engine()
    n_chunks = engine.ingest_document(text)

    doc_id = str(uuid.uuid4())[:8]
    global active_doc_id
    active_doc_id = doc_id
    conn = sqlite3.connect(DB)
    # Store full text so queries after restart still use the real document
    conn.execute(
        "INSERT INTO documents VALUES (?,?,?,?,?)",
        (doc_id, file.filename, text, n_chunks, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "chunks": n_chunks,
        "chars": len(text),
        "preview": text[:400],
        "mode": "demo" if engine.demo else "live",
    }


@app.get("/api/documents")
async def list_documents():
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, name, chunks, uploaded_at FROM documents ORDER BY uploaded_at DESC"
    ).fetchall()
    conn.close()
    return [
        {"id": r[0], "name": r[1], "chunks": r[2], "uploaded_at": r[3]} for r in rows
    ]


@app.post("/api/query", response_model=QueryResponse)
async def query_document(req: QueryRequest):
    global active_doc_id
    engine = get_engine()
    # Re-ingest whenever doc changes or memory was cleared — never ignore uploaded text
    if active_doc_id != req.doc_id or not engine.chunks:
        load_document_into_engine(req.doc_id)

    result = engine.query(req.question)

    query_id = str(uuid.uuid4())[:8]
    grades_data = [
        {
            "grade": g.grade,
            "confidence": g.confidence,
            "reasoning": g.reasoning,
            "passage": g.passage,
        }
        for g in result.grades
    ]

    conn = sqlite3.connect(DB)
    conn.execute(
        "INSERT INTO queries VALUES (?,?,?,?,?,?,?,?)",
        (
            query_id,
            req.doc_id,
            req.question,
            result.final_answer,
            result.corrective_action,
            int(result.was_corrected),
            json.dumps(grades_data),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    return QueryResponse(
        id=query_id,
        question=req.question,
        answer=result.final_answer,
        action=result.corrective_action,
        was_corrected=result.was_corrected,
        grades=grades_data,
        passages_used=len(result.final_passages),
        mode=getattr(result, "mode", "demo" if engine.demo else "live"),
    )


@app.get("/api/history/{doc_id}")
async def get_history(doc_id: str):
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, question, answer, action, was_corrected, created_at FROM queries WHERE doc_id=? ORDER BY created_at DESC",
        (doc_id,),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "question": r[1],
            "answer": r[2],
            "action": r[3],
            "was_corrected": bool(r[4]),
            "created_at": r[5],
        }
        for r in rows
    ]


@app.get("/api/history")
async def get_all_history():
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        """
        SELECT q.id, q.doc_id, d.name, q.question, q.answer, q.action,
               q.was_corrected, q.created_at
        FROM queries q
        LEFT JOIN documents d ON d.id = q.doc_id
        ORDER BY q.created_at DESC
        LIMIT 50
        """
    ).fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "doc_id": r[1],
            "doc_name": r[2],
            "question": r[3],
            "answer": r[4],
            "action": r[5],
            "was_corrected": bool(r[6]),
            "created_at": r[7],
        }
        for r in rows
    ]


@app.get("/api/stats")
async def get_stats():
    conn = sqlite3.connect(DB)
    docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    queries = conn.execute("SELECT COUNT(*) FROM queries").fetchone()[0]
    corrected = conn.execute(
        "SELECT COUNT(*) FROM queries WHERE was_corrected=1"
    ).fetchone()[0]
    actions = conn.execute(
        "SELECT action, COUNT(*) FROM queries GROUP BY action"
    ).fetchall()
    recent = conn.execute(
        """
        SELECT q.question, q.action, q.was_corrected, q.created_at, d.name
        FROM queries q LEFT JOIN documents d ON d.id = q.doc_id
        ORDER BY q.created_at DESC LIMIT 5
        """
    ).fetchall()
    conn.close()

    engine = qa_engine
    return {
        "documents": docs,
        "queries": queries,
        "corrected_queries": corrected,
        "correction_rate": round(corrected / queries, 3) if queries else 0,
        "actions": {a: c for a, c in actions},
        "model_loaded": engine is not None,
        "demo_mode": bool(getattr(engine, "demo", True)) if engine else os.getenv("DEMO_MODE", "0") == "1",
        "recent": [
            {
                "question": r[0],
                "action": r[1],
                "was_corrected": bool(r[2]),
                "created_at": r[3],
                "doc_name": r[4],
            }
            for r in recent
        ],
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "model_loaded": qa_engine is not None,
        "demo_mode": os.getenv("DEMO_MODE", "0") == "1",
        "generator_llm": getattr(qa_engine, "generator_model", "not loaded")
        if qa_engine
        else "not loaded",
        "active_doc_id": active_doc_id,
        "chunks_loaded": len(getattr(qa_engine, "chunks", []) or []) if qa_engine else 0,
        "module": "confidence-gated-corrective-rag",
        "rag_efficient": False,
        "note": "RAG works; efficiency upgrades pending — see docs/RAG_EFFICIENCY.md",
    }
