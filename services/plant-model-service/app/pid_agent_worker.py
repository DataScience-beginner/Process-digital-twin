"""DB-backed P&ID candidate-recognition agent.

All source bytes and provisional outputs stay in the project database. This
worker has no external AI/model-training calls and no route to publish a
physical pipe graph. The queue uses Postgres row locks for concurrent workers.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine, or_, select, update
from sqlalchemy.engine import Engine

from .agent_pilot_gateway import SCHEMA, companies, documents, events, projects, questions, recognition_jobs

MAX_OUTPUT_BYTES = 24 * 1024 * 1024
LEASE_SECONDS = 600
MAX_ATTEMPTS = 2


def _utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _event(db, tenant_id, project_id, code):
    db.execute(events.insert().values(id=uuid4().hex, company_id=tenant_id,
        project_id=project_id, agent="pid_candidate_recognition_agent",
        event_code=code, created_at=_utc()))


def _question(db, tenant_id, project_id, code, message):
    prior = db.execute(select(questions.c.id).where(
        questions.c.company_id == tenant_id, questions.c.project_id == project_id,
        questions.c.code == code, questions.c.status == "open")).first()
    if not prior:
        db.execute(questions.insert().values(id=uuid4().hex,
            company_id=tenant_id, project_id=project_id, code=code,
            message=message, status="open"))


def claim(engine: Engine):
    """Claim one queued job; recover abandoned leases without double claiming.

    The transaction locks a job row on PostgreSQL, then transitions both the
    job and its document. Interrupted workers may retry once after 10 minutes.
    """
    cutoff = _utc() - timedelta(seconds=LEASE_SECONDS)
    with engine.begin() as db:
        # Old jobs with exhausted attempts are no longer silently orphaned.
        exhausted = db.execute(select(recognition_jobs).where(
            recognition_jobs.c.state == "processing",
            recognition_jobs.c.started_at < cutoff,
            recognition_jobs.c.attempts >= MAX_ATTEMPTS
        ).with_for_update(skip_locked=True)).mappings().all()
        for blocked in exhausted:
            db.execute(update(recognition_jobs).where(recognition_jobs.c.id == blocked["id"]).values(
                state="needs_engineering_review", error_code="worker_timeout_review_required", completed_at=_utc()))
            db.execute(update(documents).where(documents.c.id == blocked["document_id"],
                documents.c.company_id == blocked["company_id"],
                documents.c.project_id == blocked["project_id"]).values(status="needs_engineering_review"))
            _question(db, blocked["company_id"], blocked["project_id"], "WORKER_TIMEOUT",
                "The preliminary recognition worker did not finish. Please request an engineering review.")
            _event(db, blocked["company_id"], blocked["project_id"], "recognition_timeout_requires_review")
        row = db.execute(select(recognition_jobs).where(or_(
            recognition_jobs.c.state == "queued",
            (recognition_jobs.c.state == "processing") &
            (recognition_jobs.c.started_at < cutoff) &
            (recognition_jobs.c.attempts < MAX_ATTEMPTS)
        )).order_by(recognition_jobs.c.created_at, recognition_jobs.c.id)
            .with_for_update(skip_locked=True).limit(1)).mappings().first()
        if row is None:
            return None
        doc = db.execute(select(documents.c.id, documents.c.kind,
            documents.c.company_id, documents.c.project_id, documents.c.status)
            .where(documents.c.id == row["document_id"])).first()
        if not doc or doc.kind != "pid" or doc.company_id != row["company_id"] or doc.project_id != row["project_id"] or doc.status not in ("ready_for_recognition", "recognizing"):
            db.execute(update(recognition_jobs).where(recognition_jobs.c.id == row["id"]).values(
                state="blocked_invalid_source", error_code="invalid_or_cross_tenant_document"))
            _event(db, row["company_id"], row["project_id"], "recognition_blocked_invalid_source")
            return None
        project = db.execute(select(projects.c.id).where(
            projects.c.id == row["project_id"], projects.c.company_id == row["company_id"])).first()
        company = db.execute(select(companies.c.id).where(companies.c.id == row["company_id"])).first()
        if project is None or company is None:
            db.execute(update(recognition_jobs).where(recognition_jobs.c.id == row["id"]).values(
                state="blocked_invalid_source", error_code="missing_company_or_project"))
            return None
        db.execute(update(recognition_jobs).where(recognition_jobs.c.id == row["id"]).values(
            state="processing", attempts=row["attempts"] + 1, started_at=_utc()))
        db.execute(update(documents).where(documents.c.id == row["document_id"]).values(status="recognizing"))
        _event(db, row["company_id"], row["project_id"], "candidate_recognition_started")
    return dict(row)


def execute_one(engine: Engine, *, processor=None) -> dict:
    """Perform one job. Caller controls scheduling; no implicit external calls."""
    job = claim(engine)
    if not job:
        return {"processed": False, "reason": "queue_empty_or_unclaimable"}
    if processor is None:
        from .pid60_pipeline import process_single_page
        processor = process_single_page
    with engine.connect() as db:
        doc = db.execute(select(documents).where(
            documents.c.id == job["document_id"],
            documents.c.company_id == job["company_id"],
            documents.c.project_id == job["project_id"])).mappings().one()
    try:
        # The stored source is already a single selected PDF page.
        raw = doc["source_page"]
        result = processor(raw, 1)
        graph = dict(result["graph"])
        if not graph.get("provisional_graph_only") or graph.get("publish_ready") is not False:
            raise ValueError("non_provisional_graph_not_allowed")
        physical = graph.get("edges", {}).get("engineering_approved_physical_connections")
        if physical != []:
            raise ValueError("physical_edge_gate_violation")
        graph["original_source"] = {
            "original_pdf_sha256": doc["sha256"], "original_page_1based": doc["page_number"],
            "document_id": doc["id"], "source_evidence_reviewed": False,
        }
        png, pdf = result["overlay_png"], result["annotated_pdf"]
        if not (png.startswith(b"\x89PNG\r\n\x1a\n") and pdf.startswith(b"%PDF-")):
            raise ValueError("invalid_preview_artifact")
        if len(png) + len(pdf) > MAX_OUTPUT_BYTES:
            raise ValueError("preview_artifacts_too_large")
        stats = dict(result["summary"])
        if stats.get("accepted_physical_graph_edges", -1) != 0:
            raise ValueError("engineering_edge_approval_violation")
        with engine.begin() as db:
            # Lease ownership guard: never replace a completed or superseded job.
            state = db.execute(select(recognition_jobs.c.state).where(
                recognition_jobs.c.id == job["id"]).with_for_update()).scalar_one()
            attempt = db.execute(select(recognition_jobs.c.attempts).where(
                recognition_jobs.c.id == job["id"])).scalar_one()
            if state != "processing" or attempt != job["attempts"] + 1:
                return {"processed": False, "reason": "job_state_changed"}
            db.execute(update(recognition_jobs).where(recognition_jobs.c.id == job["id"]).values(
                state="candidate_review_ready", graph_json=graph, summary_json=stats,
                benchmark_json=result.get("benchmark", {}), artifact_png=png,
                artifact_pdf=pdf, completed_at=_utc(), error_code=None))
            db.execute(update(documents).where(documents.c.id == doc["id"]).values(
                status="candidate_review_ready"))
            _question(db, job["company_id"], job["project_id"], "REVIEW_CANDIDATES",
                "The drawing's graphical candidates are ready. Review source-linked symbols, exact legend class, tees/crossings and pipe connectivity. No physical connections are approved.")
            _event(db, job["company_id"], job["project_id"], "candidate_markup_ready_not_engineering_approved")
        return {"processed": True, "state": "candidate_review_ready", "document_id": doc["id"],
                "candidate_motifs": stats.get("whole_sheet_complete_glyph_geometry_count", 0)}
    except (ValueError, RuntimeError, IndexError, MemoryError) as exc:
        # Expose only a controlled error code; never log raw client PDFs or prompt text.
        error_code = "unsupported_or_invalid_vector_pdf"
        if str(exc) in ("non_provisional_graph_not_allowed", "physical_edge_gate_violation",
                        "invalid_preview_artifact", "preview_artifacts_too_large",
                        "engineering_edge_approval_violation"):
            error_code = "output_integrity_failed"
        with engine.begin() as db:
            active = db.execute(select(recognition_jobs.c.state, recognition_jobs.c.attempts).where(
                recognition_jobs.c.id == job["id"]).with_for_update()).first()
            if active is None or active.state != "processing" or active.attempts != job["attempts"] + 1:
                return {"processed": False, "reason": "job_state_changed"}
            db.execute(update(recognition_jobs).where(recognition_jobs.c.id == job["id"]).values(
                state="needs_engineering_review", error_code=error_code, completed_at=_utc()))
            db.execute(update(documents).where(documents.c.id == job["document_id"]).values(
                status="needs_engineering_review"))
            _question(db, job["company_id"], job["project_id"], "UNSUPPORTED_DRAWING",
                "The drawing cannot be safely processed in the vector workflow. Please request engineering review; scanned P&IDs require a separate OCR pipeline.")
            _event(db, job["company_id"], job["project_id"], "candidate_recognition_needs_review")
        return {"processed": True, "state": "needs_engineering_review", "error_code": error_code}


def worker_main():
    if os.getenv("AGENT_WORKER_ENABLED", "false").lower() != "true":
        raise RuntimeError("Set AGENT_WORKER_ENABLED=true only for isolated, approved staging/workspaces")
    uri = os.getenv("AGENT_DATABASE_URL", "")
    if not uri:
        raise RuntimeError("AGENT_DATABASE_URL must be configured")
    if uri.startswith("postgres://"):
        uri = "postgresql+psycopg://" + uri[len("postgres://"):]
    elif uri.startswith("postgresql://"):
        uri = "postgresql+psycopg://" + uri[len("postgresql://"):]
    engine = create_engine(uri, pool_pre_ping=True)
    SCHEMA.create_all(engine)
    print("pid-candidate-recognition worker started; source contents not logged", flush=True)
    while True:
        try:
            result = execute_one(engine)
            if result["processed"]:
                print("job completed state:", result["state"], flush=True)
            else:
                time.sleep(4)
        except Exception:
            # Unknown failures are neither converted to successful graphs nor logged
            # with sensitive payloads. The lease permits one later replay.
            print("worker exception; job remains fail-closed", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    worker_main()