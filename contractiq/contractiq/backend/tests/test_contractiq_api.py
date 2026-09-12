"""ContractIQ API tests — isolated module load."""
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
SAMPLE = BACKEND.parent / "samples" / "sample_msa.txt"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    # Ensure backend dir is first for sibling imports inside main
    sys.path.insert(0, str(BACKEND))
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Clear conflicting modules
    for key in list(sys.modules):
        if key in {"main", "core"} or key.startswith("contractiq_"):
            if key in {"main", "core"}:
                sys.modules.pop(key, None)

    monkeypatch.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    # Load core then main under unique names, but main expects `import core`
    core = _load("core", BACKEND / "core.py")
    sys.modules["core"] = core
    appmod = _load("contractiq_main_test", BACKEND / "main.py")

    db = tmp_path / "test.db"
    monkeypatch.setattr(appmod, "DB", str(db))
    appmod.init_db()
    appmod.qa_engine = None
    if hasattr(appmod, "active_doc_id"):
        appmod.active_doc_id = None
    with TestClient(appmod.app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "generator_llm" in body
    assert body.get("rag_efficient") is False


def test_upload_and_query_uses_document(client):
    assert SAMPLE.exists()
    with SAMPLE.open("rb") as f:
        up = client.post("/api/upload", files={"file": ("sample_msa.txt", f, "text/plain")})
    assert up.status_code == 200, up.text
    doc_id = up.json()["doc_id"]
    assert up.json()["chunks"] >= 1

    q = client.post(
        "/api/query",
        json={"doc_id": doc_id, "question": "What is the termination notice period?"},
    )
    assert q.status_code == 200, q.text
    data = q.json()
    assert data["answer"]
    assert data["action"] in {"ACCEPT", "RE_RETRIEVE", "WEB_SEARCH"}
    blob = (data["answer"] + " " + " ".join(g.get("passage", "") for g in data["grades"])).lower()
    assert any(tok in blob for tok in ("terminat", "notice", "thirty", "30", "day"))


def test_stats_and_history(client):
    with SAMPLE.open("rb") as f:
        doc_id = client.post(
            "/api/upload", files={"file": ("sample_msa.txt", f, "text/plain")}
        ).json()["doc_id"]
    client.post(
        "/api/query",
        json={"doc_id": doc_id, "question": "What is the monthly retainer?"},
    )
    stats = client.get("/api/stats").json()
    assert stats["documents"] >= 1
    assert stats["queries"] >= 1
    hist = client.get("/api/history").json()
    assert len(hist) >= 1
