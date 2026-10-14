"""API for local P&ID document intake, review, and traceable plant drafts."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import fitz
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db_schema import Base, engine_from_url
from .persistence import PROJECT_ID, ensure_demo_seeded
from .pid_digitization import MAX_PDF_BYTES, accepted_plant_draft, extract_pid_pdf


class PidImportRow(Base):
    __tablename__ = "pid_digitization_imports"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(100), index=True)
    filename: Mapped[str] = mapped_column(String(250))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    state: Mapped[str] = mapped_column(String(40), default="awaiting_review")
    extraction_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime)


router = APIRouter(tags=["P&ID digitization"])


@lru_cache(maxsize=1)
def _database():
    engine = engine_from_url(os.getenv(
        "DATABASE_URL", "sqlite+pysqlite:///digital_bdep_demo.db"
    ))
    ensure_demo_seeded(engine)
    return engine


def _storage() -> Path:
    directory = Path(os.getenv("BDEP_PID_STORAGE", "./pid_documents")).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _load(session: Session, import_id: str) -> PidImportRow:
    row = session.get(PidImportRow, import_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Unknown P&ID import")
    return row


def _public(row: PidImportRow) -> dict:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "filename": row.filename,
        "state": row.state,
        "created_at": row.created_at.isoformat(),
        **row.extraction_json,
    }


class TagDecision(BaseModel):
    candidate_id: str
    decision: str = Field(pattern="^(accepted|rejected|unreviewed)$")


class ReviewPayload(BaseModel):
    reviewer: str = Field(min_length=2, max_length=120)
    decisions: list[TagDecision] = Field(min_length=1)


@router.post("/api/pid-digitization/imports")
async def import_pid_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(415, detail="This MVP supports PDF uploads only")
    try:
        contents = await file.read(MAX_PDF_BYTES + 1)
    finally:
        await file.close()
    try:
        extracted = extract_pid_pdf(contents)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    import_id = f"PID-{uuid4().hex}"
    storage_path = _storage() / f"{import_id}.pdf"
    storage_path.write_bytes(contents)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        with Session(_database()) as session:
            row = PidImportRow(
                id=import_id,
                project_id=PROJECT_ID,
                filename=Path(file.filename).name[:250],
                sha256=extracted["document_sha256"],
                state="awaiting_review",
                extraction_json={**extracted, "review_history": []},
                created_at=now,
            )
            session.add(row)
            session.commit()
            return _public(row)
    except Exception:
        storage_path.unlink(missing_ok=True)
        raise


@router.get("/api/pid-digitization/imports/{import_id}")
def get_pid_import(import_id: str):
    with Session(_database()) as session:
        return _public(_load(session, import_id))


@router.post("/api/pid-digitization/imports/{import_id}/review")
def review_pid_tags(import_id: str, payload: ReviewPayload):
    with Session(_database()) as session:
        row = _load(session, import_id)
        extracted = dict(row.extraction_json)
        known = {c["id"] for c in extracted["candidates"]}
        unknown = {decision.candidate_id for decision in payload.decisions} - known
        if unknown:
            raise HTTPException(422, detail=f"Unknown candidate IDs: {sorted(unknown)}")
        decisions = {decision.candidate_id: decision.decision for decision in payload.decisions}
        for candidate in extracted["candidates"]:
            if candidate["id"] in decisions:
                candidate["review_status"] = decisions[candidate["id"]]
                candidate["reviewed_by"] = payload.reviewer
        extracted["review_history"] = [
            *extracted.get("review_history", []),
            {
                "reviewed_by": payload.reviewer,
                "decisions": len(payload.decisions),
                "at": datetime.now(timezone.utc).isoformat(),
            },
        ]
        row.extraction_json = extracted
        row.state = (
            "tags_reviewed"
            if all(c["review_status"] != "unreviewed" for c in extracted["candidates"])
            else "awaiting_review"
        )
        session.commit()
        return _public(row)


@router.get("/api/pid-digitization/imports/{import_id}/plant-draft")
def get_pid_plant_draft(import_id: str):
    with Session(_database()) as session:
        row = _load(session, import_id)
        return accepted_plant_draft(
            row.id, row.project_id, row.extraction_json["candidates"]
        )


@router.get("/api/pid-digitization/imports/{import_id}/pages/{page_number}.png")
def get_pid_page_preview(import_id: str, page_number: int):
    with Session(_database()) as session:
        row = _load(session, import_id)
        page_count = int(row.extraction_json["page_count"])
    if not (1 <= page_number <= page_count):
        raise HTTPException(404, detail="Page does not exist")
    source = _storage() / f"{row.id}.pdf"
    if not source.is_file():
        raise HTTPException(404, detail="Source file not available")
    with fitz.open(source) as doc:
        page = doc[page_number - 1]
        zoom = min(1.6, 1800 / max(page.rect.width, page.rect.height))
        png = page.get_pixmap(
            matrix=fitz.Matrix(zoom, zoom), alpha=False
        ).tobytes("png")
    return Response(
        png, media_type="image/png",
        headers={"Cache-Control": "private, no-store"},
    )
