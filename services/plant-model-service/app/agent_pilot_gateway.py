"""Isolated, fail-closed company onboarding and P&ID pilot agents.

Serve this app on Railway, never the older demo app.main:app. All clients
require provisioned, company-scoped credentials. No LLM/provider calls occur.
Recognition remains a separate, engineering-gated pipeline.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone
from uuid import uuid4

import fitz
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import (Column, DateTime, ForeignKey, Integer, LargeBinary,
                        MetaData, String, Table, UniqueConstraint, create_engine,
                        select, update)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from .tenant_data_governance import DeploymentMode, TenantPolicy

MAX_SOURCE_BYTES = 40 * 1024 * 1024
MAX_PAGE_BYTES = 12 * 1024 * 1024
MAX_PAGES = 300
SCHEMA = MetaData()
companies = Table("agent_pilot_companies", SCHEMA,
    Column("id", String(40), primary_key=True),
    Column("normalized_name", String(200), unique=True, nullable=False),
    Column("name", String(200), nullable=False),
    Column("deployment_mode", String(40), nullable=False),
    Column("access_hash", String(64), nullable=False),
    Column("free_used", Integer, nullable=False, default=0),
    Column("paid_credits", Integer, nullable=False, default=0),
)
projects = Table("agent_pilot_projects", SCHEMA,
    Column("id", String(40), primary_key=True),
    Column("company_id", String(40), ForeignKey(companies.c.id), nullable=False),
    Column("name", String(200), nullable=False),
)
documents = Table("agent_pilot_documents", SCHEMA,
    Column("id", String(40), primary_key=True),
    Column("company_id", String(40), ForeignKey(companies.c.id), nullable=False),
    Column("project_id", String(40), ForeignKey(projects.c.id), nullable=False),
    Column("kind", String(15), nullable=False),
    Column("filename", String(200), nullable=False),
    Column("sha256", String(64), nullable=False),
    Column("page_number", Integer, nullable=False),
    Column("source_page", LargeBinary, nullable=False),
    Column("status", String(60), nullable=False),
    UniqueConstraint("company_id", "kind", "sha256", "page_number", name="uq_agent_pilot_source"),
)
questions = Table("agent_pilot_questions", SCHEMA,
    Column("id", String(40), primary_key=True),
    Column("company_id", String(40), ForeignKey(companies.c.id), nullable=False),
    Column("project_id", String(40), ForeignKey(projects.c.id), nullable=False),
    Column("code", String(60), nullable=False),
    Column("message", String(600), nullable=False),
    Column("status", String(20), nullable=False),
    Column("reply", String(1000), nullable=True),
)
commercial_grants = Table("agent_pilot_commercial_grants", SCHEMA,
    Column("id", String(40), primary_key=True),
    Column("company_id", String(40), nullable=False),
    Column("commercial_reference", String(100), nullable=False),
    Column("additional_credits", Integer, nullable=False),
    UniqueConstraint("company_id", "commercial_reference", name="uq_commercial_reference"),
)
events = Table("agent_pilot_events", SCHEMA,
    Column("id", String(40), primary_key=True),
    Column("company_id", String(40), nullable=False),
    Column("project_id", String(40), nullable=True),
    Column("agent", String(60), nullable=False),
    Column("event_code", String(80), nullable=False),
    Column("created_at", DateTime, nullable=False),
)


class CompanyRequest(BaseModel):
    company_name: str = Field(min_length=3, max_length=200)
    deployment_mode: DeploymentMode = DeploymentMode.MANAGED_SHARED


class ProjectRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)


class ChatReply(BaseModel):
    answer: str = Field(min_length=1, max_length=1000)


class GrantRequest(BaseModel):
    additional_credits: int = Field(ge=1, le=10000)
    commercial_reference: str = Field(min_length=4, max_length=100)


def _id() -> str:
    return uuid4().hex


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _event(db, company: str, project: str | None, agent: str, action: str):
    db.execute(events.insert().values(id=_id(), company_id=company, project_id=project,
        agent=agent, event_code=action, created_at=datetime.now(timezone.utc).replace(tzinfo=None)))


def _question(db, company: str, project: str, code: str, message: str):
    prior = db.execute(select(questions.c.id).where(
        questions.c.company_id == company, questions.c.project_id == project,
        questions.c.code == code, questions.c.status == "open")).first()
    if not prior:
        db.execute(questions.insert().values(id=_id(), company_id=company, project_id=project,
            code=code, message=message, status="open"))
        _event(db, company, project, "completeness_agent" if code == "MISSING_LEGEND"
               else "commercial_agent", code)


def _advance(db, company_id: str, project_id: str):
    """Synchronous orchestration: intake -> completeness -> quota -> recognition queue.

    Reserve conversion credits atomically under a PostgreSQL company row lock.
    Document status is ready_for_recognition, NOT an engineering graph claim.
    """
    company = db.execute(select(companies).where(companies.c.id == company_id).with_for_update()).mappings().one()
    docs = db.execute(select(documents).where(documents.c.company_id == company_id,
        documents.c.project_id == project_id)).mappings().all()
    valid_legend = any(d["kind"] == "legend" and d["status"] == "legend_observed" for d in docs)
    pending = [d for d in docs if d["kind"] == "pid" and d["status"] == "waiting_for_legend"]
    if not valid_legend:
        if pending:
            _question(db, company_id, project_id, "MISSING_LEGEND",
                      "I received your P&ID. Please upload the matching legend sheet to continue digitalization.")
        return
    db.execute(update(questions).where(questions.c.company_id == company_id,
        questions.c.project_id == project_id, questions.c.code == "MISSING_LEGEND",
        questions.c.status == "open").values(status="resolved"))
    free_used, paid_left = company["free_used"], company["paid_credits"]
    for doc in pending:
        if free_used < 2:
            free_used += 1
            new_status = "ready_for_recognition"
        elif paid_left > 0:
            paid_left -= 1
            new_status = "ready_for_recognition"
        else:
            new_status = "contact_sales_required"
            _question(db, company_id, project_id, "CONTACT_SALES",
                      "Your two-P&ID free pilot is allocated. Contact our engineering team for additional conversions.")
        db.execute(update(documents).where(documents.c.id == doc["id"]).values(status=new_status))
        _event(db, company_id, project_id, "quota_agent", new_status)
    db.execute(update(companies).where(companies.c.id == company_id).values(
        free_used=free_used, paid_credits=paid_left))


def create_app(db_url: str | None = None, *, admin_token: str | None = None,
               uploads_enabled: bool | None = None) -> FastAPI:
    uri = db_url or os.getenv("AGENT_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not uri:
        raise RuntimeError("AGENT_DATABASE_URL or DATABASE_URL is mandatory; ephemeral storage prohibited")
    if uri.startswith("postgres://"):
        uri = "postgresql+psycopg://" + uri[len("postgres://"):]
    elif uri.startswith("postgresql://"):
        uri = "postgresql+psycopg://" + uri[len("postgresql://"):]
    engine: Engine = create_engine(uri, pool_pre_ping=True)
    SCHEMA.create_all(engine)  # isolated MVP schema; Alembic + migrations needed before production
    token = admin_token if admin_token is not None else os.getenv("AGENT_ADMIN_TOKEN", "")
    enabled = uploads_enabled if uploads_enabled is not None else os.getenv("AGENT_UPLOADS_ENABLED") == "true"
    app = FastAPI(title="P&ID Agent Pilot Gateway", version="0.1.0")

    def admin(x_admin_token: str | None = Header(default=None)):
        if not token or not x_admin_token or not hmac.compare_digest(x_admin_token, token):
            raise HTTPException(403, "Unauthorized administrator")

    def tenant(x_client_token: str | None = Header(default=None)) -> str:
        if not x_client_token:
            raise HTTPException(401, "Company access token required")
        # High-entropy server-issued token; SHA-256 digest only ever stored.
        with engine.connect() as db:
            c = db.execute(select(companies.c.id, companies.c.access_hash)).all()
        hashed = _sha(x_client_token)
        for company_id, digest in c:
            if hmac.compare_digest(hashed, digest):
                return company_id
        raise HTTPException(401, "Unknown company access token")

    def ensure_project(db, company_id: str, project_id: str):
        row = db.execute(select(projects.c.id).where(projects.c.id == project_id,
            projects.c.company_id == company_id)).first()
        if not row:
            raise HTTPException(404, "Unknown project")

    @app.get("/healthz")
    def health():
        with engine.connect() as db:
            db.execute(select(companies.c.id).limit(1))
        return {"ok": True, "service": "pid-agent-onboarding", "uploads_enabled": enabled}

    @app.post("/api/admin/companies", dependencies=[Depends(admin)])
    def register_company(req: CompanyRequest):
        norm = " ".join(req.company_name.casefold().split())
        if req.deployment_mode == DeploymentMode.PRIVATE_CLOUD and os.getenv("AGENT_PRIVATE_CLOUD_DEPLOYMENT") != "true":
            raise HTTPException(409, "Private cloud requires separately provisioned deployment; contact sales")
        company_id, access_token = _id(), secrets.token_urlsafe(36)
        TenantPolicy(tenant_id=company_id, deployment_mode=req.deployment_mode)  # secure default: no training
        try:
            with engine.begin() as db:
                db.execute(companies.insert().values(id=company_id, normalized_name=norm,
                    name=req.company_name, deployment_mode=req.deployment_mode.value,
                    access_hash=_sha(access_token), free_used=0, paid_credits=0))
                _event(db, company_id, None, "onboarding_agent", "company_registered")
        except IntegrityError:
            raise HTTPException(409, "Company already registered; contact the administrator")
        return {"company_id": company_id, "company_access_token": access_token,
                "free_pid_limit": 2, "global_training_opt_in": False,
                "deployment_mode": req.deployment_mode.value}

    @app.post("/api/projects")
    def create_project(req: ProjectRequest, company_id: str = Depends(tenant)):
        project_id = _id()
        with engine.begin() as db:
            db.execute(projects.insert().values(id=project_id, company_id=company_id, name=req.name))
            _event(db, company_id, project_id, "onboarding_agent", "project_created")
        return {"project_id": project_id, "state": "waiting_for_pid"}

    @app.post("/api/projects/{project_id}/documents")
    async def upload(project_id: str, file: UploadFile = File(...),
                     kind: str = Query(..., pattern="^(pid|legend|supporting)$"),
                     page: int = Query(1, ge=1), company_id: str = Depends(tenant)):
        if not enabled:
            raise HTTPException(503, "Uploads disabled until tenant/security verification")
        with engine.connect() as db:
            ensure_project(db, company_id, project_id)
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(415, "Upload PDF only")
        try:
            original = await file.read(MAX_SOURCE_BYTES + 1)
        finally:
            await file.close()
        if len(original) > MAX_SOURCE_BYTES:
            raise HTTPException(413, "PDF exceeds 40 MiB limit")
        if not original.startswith(b"%PDF-"):
            raise HTTPException(422, "Invalid PDF signature")
        try:
            with fitz.open(stream=original, filetype="pdf") as src:
                if src.needs_pass or src.page_count > MAX_PAGES or page > src.page_count:
                    raise HTTPException(422, "PDF protected, too long or page not found")
                txt = src[page-1].get_text("text").upper()
                page_file = fitz.open()
                try:
                    page_file.insert_pdf(src, from_page=page-1, to_page=page-1)
                    selected_page = page_file.tobytes(garbage=4, deflate=True)
                finally:
                    page_file.close()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(422, "Unreadable PDF") from exc
        if len(selected_page) > MAX_PAGE_BYTES:
            raise HTTPException(413, "Selected page too large")
        sha = hashlib.sha256(original).hexdigest()
        if kind == "legend":
            # Source-text-only first pass. Scanned/ambiguous legends require human review.
            status = "legend_observed" if ("LEGEND" in txt and any(
                term in txt for term in ("VALVE", "SYMBOL", "INSTRUMENT"))) else "legend_needs_review"
        elif kind == "pid":
            status = "waiting_for_legend"
        else:
            status = "supporting_received"
        with engine.begin() as db:
            ensure_project(db, company_id, project_id)
            prior = db.execute(select(documents.c.id, documents.c.status).where(
                documents.c.company_id == company_id, documents.c.kind == kind,
                documents.c.sha256 == sha, documents.c.page_number == page)).first()
            if prior:
                return {"document_id": prior.id, "status": prior.status,
                        "duplicate": True, "free_credit_charged": False}
            doc_id = _id()
            db.execute(documents.insert().values(id=doc_id, company_id=company_id,
                project_id=project_id, kind=kind, filename=os.path.basename(file.filename or "document.pdf")[:200],
                sha256=sha, page_number=page, source_page=selected_page, status=status))
            _event(db, company_id, project_id, "document_intake_agent", kind + "_received")
            if status == "legend_needs_review":
                _question(db, company_id, project_id, "LEGEND_REVIEW",
                          "I received a possible legend, but cannot verify it from the drawing. Please request engineering review.")
            _advance(db, company_id, project_id)
            current = db.execute(select(documents.c.status).where(documents.c.id == doc_id)).scalar_one()
            credit = current == "ready_for_recognition" and kind == "pid"
        return {"document_id": doc_id, "status": current, "duplicate": False,
                "free_or_paid_credit_reserved": credit,
                "note": "Recognition and engineering graph validation are not completed by this gateway"}

    @app.get("/api/projects/{project_id}/status")
    def project_status(project_id: str, company_id: str = Depends(tenant)):
        with engine.connect() as db:
            ensure_project(db, company_id, project_id)
            company = db.execute(select(companies).where(companies.c.id == company_id)).mappings().one()
            docs = db.execute(select(documents.c.id, documents.c.kind, documents.c.page_number,
                documents.c.status).where(documents.c.company_id == company_id,
                documents.c.project_id == project_id)).mappings().all()
            chats = db.execute(select(questions.c.id, questions.c.code, questions.c.message,
                questions.c.status).where(questions.c.company_id == company_id,
                questions.c.project_id == project_id)).mappings().all()
            history = db.execute(select(events.c.agent, events.c.event_code).where(
                events.c.company_id == company_id, events.c.project_id == project_id)).mappings().all()
        return {"project_id": project_id, "free_pid_used": company["free_used"],
                "free_pid_limit": 2, "paid_credits_remaining": company["paid_credits"],
                "documents": [dict(x) for x in docs], "chat_questions": [dict(x) for x in chats],
                "agent_events": [dict(x) for x in history]}

    @app.post("/api/projects/{project_id}/chat/{question_id}/reply")
    def reply(project_id: str, question_id: str, msg: ChatReply,
              company_id: str = Depends(tenant)):
        with engine.begin() as db:
            ensure_project(db, company_id, project_id)
            q = db.execute(select(questions.c.id, questions.c.code).where(
                questions.c.id == question_id, questions.c.company_id == company_id,
                questions.c.project_id == project_id)).first()
            if not q:
                raise HTTPException(404, "Unknown question")
            db.execute(update(questions).where(questions.c.id == question_id).values(reply=msg.answer))
            _event(db, company_id, project_id, "chat_agent", "user_replied_" + q.code)
        return {"received": True, "next_step": "Upload the requested document or await engineering team review"}

    @app.post("/api/admin/companies/{company_id}/grant", dependencies=[Depends(admin)])
    def grant(company_id: str, req: GrantRequest):
        with engine.begin() as db:
            company = db.execute(select(companies).where(companies.c.id == company_id).with_for_update()).first()
            if not company:
                raise HTTPException(404, "Unknown company")
            try:
                db.execute(commercial_grants.insert().values(id=_id(), company_id=company_id,
                    commercial_reference=req.commercial_reference, additional_credits=req.additional_credits))
            except IntegrityError:
                raise HTTPException(409, "Commercial reference already applied")
            db.execute(update(companies).where(companies.c.id == company_id).values(
                paid_credits=companies.c.paid_credits + req.additional_credits))
            _event(db, company_id, None, "commercial_agent", "commercial_grant_recorded")
            ids = [x[0] for x in db.execute(select(projects.c.id).where(projects.c.company_id == company_id))]
            for pid in ids:
                db.execute(update(documents).where(documents.c.project_id == pid,
                    documents.c.company_id == company_id,
                    documents.c.status == "contact_sales_required").values(status="waiting_for_legend"))
                _advance(db, company_id, pid)
        return {"granted": req.additional_credits, "reference_recorded": True}

    return app


# Railway process entry point. Keep demo / legacy FastAPI routes off this app.
# No SQLite fallback when the deployment is missing a persistent database.
if os.getenv("AGENT_DATABASE_URL") or os.getenv("DATABASE_URL"):
    app = create_app()
else:
    app = FastAPI(title="Unconfigured P&ID Agent Gateway")
    @app.get("/healthz")
    def needs_configuration():
        raise HTTPException(503, "Persistent database not configured")