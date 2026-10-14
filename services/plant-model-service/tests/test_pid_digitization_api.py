"""HTTP regression tests for PDF import, review and draft generation."""
import fitz
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.db_schema import Base
from app import pid_digitization_api as pid


def _pdf_bytes():
    """Include actual vector symbols: tag text alone cannot certify a shape."""
    document = fitz.open()
    page = document.new_page(width=760, height=360)
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(55, 70, 150, 210))
    shape.draw_circle(fitz.Point(300, 140), 30)
    shape.draw_polyline([(420, 115), (445, 140), (420, 165), (420, 115)])
    shape.draw_polyline([(470, 115), (445, 140), (470, 165), (470, 115)])
    shape.finish(color=(0, 0, 0), width=1.5)
    shape.commit()
    page.insert_text((75, 102), "V-101")
    page.insert_text((281, 198), "P-101")
    page.insert_text((419, 92), "FCV-101")
    page.insert_text((542, 150), "PSV-101")
    data = document.tobytes()
    document.close()
    return data


def test_upload_review_preview_and_unconnected_draft(monkeypatch, tmp_path):
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(pid, "_database", lambda: engine)
    monkeypatch.setenv("BDEP_PID_STORAGE", str(tmp_path))
    app = FastAPI()
    app.include_router(pid.router)
    client = TestClient(app)

    uploaded = client.post(
        "/api/pid-digitization/imports",
        files={"file": ("demo.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert uploaded.status_code == 200, uploaded.text
    payload = uploaded.json()
    assert len(payload["candidates"]) >= 3
    import_id = payload["id"]

    preview = client.get(f"/api/pid-digitization/imports/{import_id}/pages/1.png")
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/png"

    decisions = [
        {"candidate_id": c["id"], "decision": "accepted"}
        for c in payload["candidates"]
    ]
    reviewed = client.post(
        f"/api/pid-digitization/imports/{import_id}/review",
        json={"reviewer": "eng-tester", "decisions": decisions},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["state"] == "tags_reviewed"

    no_labels = client.get(f"/api/pid-digitization/imports/{import_id}/annotations")
    assert no_labels.status_code == 200
    assert no_labels.json()["annotations"] == []  # tag review does not imply symbol review
    symbols = [s for s in reviewed.json()["symbol_hypotheses"]
               if s.get("geometry_id")]
    assert symbols
    checked = client.post(
        f"/api/pid-digitization/imports/{import_id}/symbols/review",
        json={"reviewer": "eng-tester",
              "decisions": [{"tag_candidate_id": symbol["tag_id"],
                             "decision": "accepted"} for symbol in symbols]},
    )
    assert checked.status_code == 200, checked.text
    annotation = client.get(f"/api/pid-digitization/imports/{import_id}/annotations")
    assert annotation.status_code == 200
    labels = annotation.json()
    assert labels["annotations"]
    assert all(a["bbox"][2] > 0 and a["bbox"][3] > 0
               for a in labels["annotations"])
    assert all(a["reviewed_by"] == "eng-tester" for a in labels["annotations"])

    draft = client.get(f"/api/pid-digitization/imports/{import_id}/plant-draft")
    assert draft.status_code == 200
    assert draft.json()["publish_ready"] is False
    assert not draft.json()["plant_model"]["connections"]


def test_reject_non_pdf_upload(monkeypatch, tmp_path):
    monkeypatch.setenv("BDEP_PID_STORAGE", str(tmp_path))
    client = TestClient(FastAPI())
    client.app.include_router(pid.router)
    response = client.post(
        "/api/pid-digitization/imports",
        files={"file": ("bad.pdf", b"bad content", "application/pdf")},
    )
    assert response.status_code == 422
