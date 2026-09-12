"""InvoiceIQ API tests — isolated module load."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["DEMO_MODE"] = "1"
os.environ["FORCE_DEMO"] = "1"

BACKEND = Path(__file__).resolve().parents[1]
SAMPLES = BACKEND.parent / "samples"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def client(tmp_path, monkeypatch):
    for key in ("main", "core"):
        sys.modules.pop(key, None)
    monkeypatch.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    core = _load("core", BACKEND / "core.py")
    sys.modules["core"] = core
    appmod = _load("invoiceiq_main_test", BACKEND / "main.py")
    db = tmp_path / "test.db"
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setattr(appmod, "DB", str(db))
    monkeypatch.setattr(appmod, "UPLOADS", str(uploads))
    appmod.init_db()
    appmod.extractor = None
    with TestClient(appmod.app) as c:
        yield c, appmod


def test_health(client):
    c, _ = client
    r = c.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_extract_text_pdf_real_fields(client):
    c, _ = client
    path = SAMPLES / "sample_invoice_text.pdf"
    assert path.exists()
    with path.open("rb") as f:
        r = c.post(
            "/api/extract",
            files={"file": ("sample_invoice_text.pdf", f, "application/pdf")},
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["mode"] in {"pdf", "ocr", "vlm"}
    fields = {f["field_name"]: f["value"] for f in data["fields"]}
    assert "Acme" in fields.get("Vendor Name", "")
    inv = fields.get("Invoice Number", "")
    assert "INV" in inv.upper() and any(ch.isdigit() for ch in inv)
    assert data["total_amount"] == pytest.approx(23010.0, rel=0.01)


def test_extract_png_when_tesseract_available(client):
    c, _ = client
    path = SAMPLES / "sample_invoice.png"
    assert path.exists()
    with path.open("rb") as f:
        r = c.post(
            "/api/extract",
            files={"file": ("sample_invoice.png", f, "image/png")},
        )
    assert r.status_code == 200, r.text
    data = r.json()
    values = " ".join(f["value"] for f in data["fields"]).lower()
    assert "221b baker" not in values
    if data["mode"] in {"ocr", "vlm", "pdf"}:
        fields = {f["field_name"]: f["value"] for f in data["fields"]}
        assert fields.get("Vendor Name") or fields.get("Invoice Number") or data["total_amount"]


def test_different_files_differ(client):
    c, appmod = client
    with (SAMPLES / "sample_invoice_text.pdf").open("rb") as f:
        a = c.post(
            "/api/extract",
            files={"file": ("sample_invoice_text.pdf", f, "application/pdf")},
        ).json()
    from PIL import Image

    blank = Path(appmod.UPLOADS) / "blank.png"
    Image.new("RGB", (200, 200), "white").save(blank)
    with blank.open("rb") as f:
        b = c.post(
            "/api/extract",
            files={"file": ("blank.png", f, "image/png")},
        ).json()
    assert a["id"] != b["id"]
    assert a["total_amount"] == pytest.approx(23010.0, rel=0.01)
