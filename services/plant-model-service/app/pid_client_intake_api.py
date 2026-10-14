"""Prototype multi-drawing client intake.

No remote extraction service and no automatic publication. Company projects
require authorized isolation/SSO before confidential P&IDs can be uploaded.
"""
from __future__ import annotations

import io
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import fitz
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db_schema import Base
from .pid_client_intake import (
    MAX_DOCUMENT_BYTES, extract_single_page, preflight_pdf,
)
from .pid_pipeline import build_pid_extraction
from .pid_digitization_api import (
    PidImportRow, _database, _public, _storage,
)
from .pid_client_intake_renderer import render_pid_client_intake_html
from .persistence import PROJECT_ID

MAX_PACKAGE_FILES = 12
MAX_PACKAGE_BYTES = 70 * 1024 * 1024
ROLE_CHOICES = {"legend", "pid", "index", "context", "unknown"}


class PidClientBatchRow(Base):
    __tablename__ = "pid_digitization_client_batches"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(100), index=True)
    client_label: Mapped[str] = mapped_column(String(120))
    package_label: Mapped[str] = mapped_column(String(160))
    manifest_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class SheetDecision(BaseModel):
    document_id: str
    page: int = Field(ge=1)
    role: str = Field(pattern="^(legend|pid|index|context|unknown)$")


class LegendDecision(BaseModel):
    document_id: str
    legend_term_id: str
    decision: str = Field(pattern="^(accepted|rejected|unreviewed)$")


class LegendReview(BaseModel):
    reviewer: str = Field(min_length=2, max_length=120)
    decisions: list[LegendDecision] = Field(min_length=1, max_length=150)


class SheetReview(BaseModel):
    reviewer: str = Field(min_length=2, max_length=120)
    decisions: list[SheetDecision] = Field(min_length=1, max_length=100)


router = APIRouter(tags=["P&ID client package intake"])


def _load(session: Session, batch_id: str) -> PidClientBatchRow:
    row = session.get(PidClientBatchRow, batch_id)
    if row is None:
        raise HTTPException(404, detail="Unknown client drawing package")
    return row


def _public(row: PidClientBatchRow) -> dict:
    return {
        "id": row.id, "project_id": row.project_id,
        "client_label": row.client_label, "package_label": row.package_label,
        "created_at": row.created_at.isoformat(),
        **row.manifest_json,
    }


def _doc(row: PidClientBatchRow, doc_id: str) -> dict:
    for doc in row.manifest_json.get("documents", []):
        if doc["id"] == doc_id:
            return doc
    raise HTTPException(404, detail="Unknown package document")


def _file_path(batch_id: str, doc_id: str) -> Path:
    # All IDs are generated UUID hex, never raw supplied filenames.
    for identifier in (batch_id, doc_id):
        if len(identifier) < 10 or not identifier.replace("-", "").isalnum():
            raise HTTPException(400, detail="Malformed package identifier")
    return _storage() / batch_id / f"{doc_id}.pdf"


def _validate_package(documents: list[dict]) -> dict:
    accepted_legends = [
        {"document_id": d["id"], "page": p["page"]}
        for d in documents for p in d["preflight"]["pages"]
        if p["role"] == "legend" and p["role_review_status"] == "accepted"
    ]
    accepted_pid = [
        {"document_id": d["id"], "page": p["page"]}
        for d in documents for p in d["preflight"]["pages"]
        if p["role"] == "pid" and p["role_review_status"] == "accepted"
    ]
    return {
        "legend_sheets_approved": accepted_legends,
        "pid_sheets_approved": accepted_pid,
        "readiness": (
            "ready_for_pagewise_evidence_extraction"
            if accepted_legends and accepted_pid
            else "needs_legend_and_pid_role_review"
        ),
        "client_legend_is_not_symbol_ground_truth": True,
    }


@router.post("/api/pid-digitization/client-batches")
async def create_client_batch(
    files: list[UploadFile] = File(...),
    client_label: str = Form(..., min_length=2, max_length=120),
    package_label: str = Form(..., min_length=2, max_length=160),
):
    if not (1 <= len(files) <= MAX_PACKAGE_FILES):
        raise HTTPException(422, detail="Submit 1–12 PDF documents per package")
    batch_id = f"BATCH-{uuid4().hex}"
    folder = _storage() / batch_id
    folder.mkdir(parents=True, exist_ok=False)
    all_documents, total = [], 0
    try:
        for uploaded in files:
            name = Path(uploaded.filename or "document.pdf").name
            if not name.lower().endswith(".pdf"):
                raise HTTPException(415, detail="Client batch currently accepts PDF only")
            try:
                data = await uploaded.read(MAX_DOCUMENT_BYTES + 1)
            finally:
                await uploaded.close()
            total += len(data)
            if total > MAX_PACKAGE_BYTES:
                raise HTTPException(413, detail="Total package exceeds 70 MB")
            try:
                result = preflight_pdf(data, name)
            except ValueError as exc:
                raise HTTPException(422, detail=str(exc)) from exc
            doc_id = f"DOC-{uuid4().hex}"
            (folder / f"{doc_id}.pdf").write_bytes(data)
            all_documents.append({"id": doc_id, "filename": name,
                                  "preflight": result})
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with Session(_database()) as session:
            row = PidClientBatchRow(
                id=batch_id, project_id=PROJECT_ID,
                client_label=client_label, package_label=package_label,
                manifest_json={"documents": all_documents, "review_events": []},
                created_at=now,
            )
            session.add(row)
            session.commit()
            return _public(row)
    except Exception:
        for child in folder.glob("*.pdf"):
            child.unlink(missing_ok=True)
        folder.rmdir()
        raise


@router.post("/api/pid-digitization/client-batches/zip")
async def create_client_batch_from_zip(
    archive: UploadFile = File(...),
    client_label: str = Form(..., min_length=2, max_length=120),
    package_label: str = Form(..., min_length=2, max_length=160),
):
    """Expand permission-cleared client ZIPs safely without extracting paths."""
    if not (archive.filename or "").lower().endswith(".zip"):
        raise HTTPException(415, detail="Provide a ZIP archive")
    try:
        packed = await archive.read(MAX_PACKAGE_BYTES + 1)
    finally:
        await archive.close()
    if len(packed) > MAX_PACKAGE_BYTES:
        raise HTTPException(413, detail="ZIP upload exceeds 70 MB")
    uploads = []
    try:
        with zipfile.ZipFile(io.BytesIO(packed)) as z:
            members = [
                item for item in z.infolist()
                if not item.is_dir() and item.filename.lower().endswith(".pdf")
            ]
            if not 1 <= len(members) <= MAX_PACKAGE_FILES:
                raise HTTPException(422, detail="ZIP needs 1–12 PDF files")
            if sum(item.file_size for item in members) > MAX_PACKAGE_BYTES:
                raise HTTPException(413, detail="Uncompressed ZIP exceeds 70 MB")
            for info in members:
                if info.file_size > MAX_DOCUMENT_BYTES:
                    raise HTTPException(413, detail="PDF inside ZIP exceeds 20 MB")
                if info.flag_bits & 1:
                    raise HTTPException(422, detail="Encrypted ZIP files not supported")
                if info.file_size > 0 and info.compress_size < max(1, info.file_size // 250):
                    raise HTTPException(422, detail="Excessive ZIP compression ratio")
                # Never extract paths from the ZIP; only validated in-memory PDFs.
                filename = Path(info.filename.replace("\\", "/")).name
                if not filename or filename.startswith("."):
                    raise HTTPException(422, detail="Unsafe ZIP document filename")
                payload = z.read(info)
                if len(payload) != info.file_size or not payload.startswith(b"%PDF-"):
                    raise HTTPException(422, detail="ZIP entry is not a valid PDF")
                uploads.append(UploadFile(filename=filename, file=io.BytesIO(payload)))
    except (zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        raise HTTPException(422, detail="Invalid or unreadable ZIP archive") from exc
    return await create_client_batch(
        files=uploads, client_label=client_label, package_label=package_label,
    )


@router.get("/api/pid-digitization/client-batches/{batch_id}")
def get_client_batch(batch_id: str):
    with Session(_database()) as session:
        return _public(_load(session, batch_id))


@router.get("/api/pid-digitization/client-batches/{batch_id}/readiness")
def client_batch_readiness(batch_id: str):
    with Session(_database()) as session:
        row = _load(session, batch_id)
        return _validate_package(row.manifest_json["documents"])


@router.post("/api/pid-digitization/client-batches/{batch_id}/roles/review")
def review_client_batch_sheets(batch_id: str, review: SheetReview):
    with Session(_database()) as session:
        row = _load(session, batch_id)
        manifest = dict(row.manifest_json)
        for decision in review.decisions:
            doc = _doc(row, decision.document_id)
            if decision.page > doc["preflight"]["page_count"]:
                raise HTTPException(422, detail="Page exceeds document page count")
        by_doc = {d["id"]: d for d in manifest["documents"]}
        stamp = datetime.now(timezone.utc).isoformat()
        for decision in review.decisions:
            page = by_doc[decision.document_id]["preflight"]["pages"][decision.page-1]
            page["role"] = decision.role
            page["role_review_status"] = "accepted"
            page["role_reviewed_by"] = review.reviewer
            page["role_reviewed_at"] = stamp
        manifest["review_events"] = [
            *manifest.get("review_events", []),
            {"event": "sheet_role_review", "reviewer": review.reviewer,
             "count": len(review.decisions), "timestamp": stamp},
        ]
        row.manifest_json = manifest
        session.commit()
        return {**_public(row), "readiness": _validate_package(manifest["documents"])}


@router.get("/api/pid-digitization/client-batches/{batch_id}/documents/{doc_id}/pages/{page}.png")
def preview_client_sheet(batch_id: str, doc_id: str, page: int):
    with Session(_database()) as session:
        row = _load(session, batch_id)
        doc_meta = _doc(row, doc_id)
        if page < 1 or page > doc_meta["preflight"]["page_count"]:
            raise HTTPException(404, detail="Drawing page does not exist")
    path = _file_path(batch_id, doc_id)
    if not path.exists():
        raise HTTPException(404, detail="Original drawing unavailable")
    with fitz.open(path) as doc:
        selected = doc[page - 1]
        zoom = min(1.6, 1800 / max(selected.rect.width, selected.rect.height))
        payload = selected.get_pixmap(
            matrix=fitz.Matrix(zoom, zoom), alpha=False,
        ).tobytes("png")
    return Response(payload, media_type="image/png",
                    headers={"Cache-Control": "private,no-store"})


@router.post("/api/pid-digitization/client-batches/{batch_id}/documents/{doc_id}/pages/{page}/analyze")
def analyze_client_sheet(batch_id: str, doc_id: str, page: int, ocr: bool = False):
    with Session(_database()) as session:
        batch = _load(session, batch_id)
        source = _doc(batch, doc_id)
        if not (1 <= page <= source["preflight"]["page_count"]):
            raise HTTPException(404, detail="Drawing page does not exist")
        p_meta = source["preflight"]["pages"][page - 1]
        if not (p_meta["role"] == "pid"
                and p_meta["role_review_status"] == "accepted"):
            raise HTTPException(
                409, detail="Engineer must classify/approve this page as P&ID first"
            )
        readiness = _validate_package(batch.manifest_json["documents"])
        if not readiness["legend_sheets_approved"]:
            raise HTTPException(409, detail="Approve at least one project legend sheet first")
        input_file = _file_path(batch_id, doc_id)
        if not input_file.exists():
            raise HTTPException(404, detail="Drawing document missing")
        original_pdf = input_file.read_bytes()
        extracted_page = extract_single_page(original_pdf, page)
        _, extracted = build_pid_extraction(
            extracted_page, f"{doc_id}-page-{page}.pdf", ocr=ocr,
        )
        extracted["client_source"] = {
            "batch_id": batch_id, "source_document_id": doc_id,
            "source_filename": source["filename"],
            "source_original_sha256": source["preflight"]["source_sha256"],
            "source_original_page": page,
            "internal_extraction_page": 1,
            "evidence_coordinate_mapping": (
                "PDF x/y unchanged by direct page copy, but extraction page 1 "
                "corresponds to original source_original_page"
            ),
            "legend_approved_sheets": readiness["legend_sheets_approved"],
            "source_revision": "unverified; no baseline merge",
        }
        extracted["legend_terms"] = [
            {**entry, "source_document_id": document["id"]}
            for document in batch.manifest_json["documents"]
            for entry in document["preflight"]["legend_terms"]
            if any(p["page"] == entry["page"] and p["role"] == "legend"
                   and p["role_review_status"] == "accepted"
                   for p in document["preflight"]["pages"])
        ]
        import_id = f"PID-{uuid4().hex}"
        storage = _storage() / f"{import_id}.pdf"
        storage.write_bytes(extracted_page)
        try:
            imported = PidImportRow(
                id=import_id, project_id=batch.project_id,
                filename=f"{source['filename']} [original page {page}]",
                sha256=extracted["document_sha256"],
                state="awaiting_review",
                extraction_json={**extracted, "review_history": []},
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            session.add(imported)
            session.commit()
        except Exception:
            storage.unlink(missing_ok=True)
            raise
        return {
            "import_id": import_id, "batch_id": batch_id,
            "source_document": doc_id, "source_original_page": page,
            "tag_candidates": len(extracted["candidates"]),
            "symbol_candidates": len(extracted["symbol_hypotheses"]),
            "connection_candidates": len(extracted["connection_proposals"]),
            "project_legend_candidates": len(extracted["legend_terms"]),
            "review_url": f"/pid-digitization?import_id={import_id}",
            "publish_ready": False,
        }


@router.post("/api/pid-digitization/client-batches/{batch_id}/legends/review")
def review_client_legend_examples(batch_id: str, review: LegendReview):
    """Approve/reject visual legend examples independently of OCR labels.

    An accepted example means an engineer reviewed the proposed source crop,
    not that our model recognizes the same shape on other P&ID drawings.
    """
    with Session(_database()) as session:
        row = _load(session, batch_id)
        manifest = dict(row.manifest_json)
        documents = {d["id"]: d for d in manifest["documents"]}
        found = {}
        for d in manifest["documents"]:
            for legend in d["preflight"]["legend_terms"]:
                found[(d["id"], legend["id"])] = (d, legend)
        for decision in review.decisions:
            key = (decision.document_id, decision.legend_term_id)
            if key not in found:
                raise HTTPException(422, detail="Unknown legend example")
            doc, legend = found[key]
            if decision.decision == "accepted":
                role = doc["preflight"]["pages"][legend["page"] - 1]
                if role["role"] != "legend" or role["role_review_status"] != "accepted":
                    raise HTTPException(409, detail="Source sheet must first be approved as legend")
                if not legend.get("proposed_symbol_crop_pdf"):
                    raise HTTPException(422, detail="No traceable visual crop")
        stamp = datetime.now(timezone.utc).isoformat()
        for decision in review.decisions:
            _, legend = found[(decision.document_id, decision.legend_term_id)]
            legend["review_status"] = decision.decision
            legend["reviewed_by"] = review.reviewer
            legend["reviewed_at"] = stamp
        manifest["review_events"] = [
            *manifest.get("review_events", []),
            {"event": "legend_example_review", "reviewer": review.reviewer,
             "count": len(review.decisions), "timestamp": stamp},
        ]
        row.manifest_json = manifest
        session.commit()
        return {
            "batch_id": batch_id,
            "accepted_legend_examples": sum(
                e["review_status"] == "accepted"
                for d in manifest["documents"]
                for e in d["preflight"]["legend_terms"]
            ),
            "reviewer": review.reviewer,
        }


@router.get("/api/pid-digitization/client-batches/{batch_id}/documents/{doc_id}/legends/{term_id}.png")
def preview_legend_example(batch_id: str, doc_id: str, term_id: str):
    with Session(_database()) as session:
        row = _load(session, batch_id)
        doc = _doc(row, doc_id)
        match = next((t for t in doc["preflight"]["legend_terms"]
                      if t["id"] == term_id), None)
        if match is None:
            raise HTTPException(404, detail="Legend sample not found")
        if doc["preflight"]["pages"][match["page"] - 1]["role"] != "legend":
            raise HTTPException(409, detail="Source page is not a legend")
        box = match["proposed_symbol_crop_pdf"]
        page_number = match["page"]
    file_path = _file_path(batch_id, doc_id)
    with fitz.open(file_path) as pdf:
        p = pdf[page_number - 1]
        clip = fitz.Rect(*box) & p.rect
        if clip.is_empty:
            raise HTTPException(422, detail="Empty legend clip")
        pix = p.get_pixmap(matrix=fitz.Matrix(3, 3),
                           clip=clip, alpha=False)
        return Response(pix.tobytes("png"), media_type="image/png",
                        headers={"Cache-Control": "private,no-store"})


@router.get("/pid-client-intake", response_class=HTMLResponse)
def client_intake_page():
    return render_pid_client_intake_html()
