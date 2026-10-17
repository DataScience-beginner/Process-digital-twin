# P&ID agent onboarding pilot (staging only)

**Source:** feature/pid-agent-onboarding-pilot based on previous Python P&ID and tenant-learning branches.

## What actually works
- Authorized administrator provisions a company; one high-entropy token returned once. Company names normalized for duplicate registration control.
- Company-scoped token creates a project and uploads one selected P&ID or legend sheet (page number explicit).
- Deterministic agents record events, detect missing legend, ask a question through the chat API, and continue when a text-observed legend is uploaded.
- Exactly two free conversion *reservations* per company globally (not per project); third becomes contact_sales_required. Admin can grant credits after independent commercial approval.
- SHA+page dedupe avoids repeated reservations for the exact original PDF bytes in one company.
- Private-cloud setup cannot be selected inside shared SaaS; contact sales for a separately isolated deployment.
- Source page bytes are held in the company-scoped pilot database. No external LLM or training call.

## Important limits / fail-closed
- "ready_for_recognition" is a queue state, **not** a converted P&ID, an annotated symbol library, or an engineering-approved graph.
- A drawing selected by page can be part of a multi-page source; pilot reservations are per original-file hash plus selected page.
- Legend role check is native-text heuristic only. Vector/raster graphics need engineering review; ambiguous legend creates LEGEND_REVIEW chat question.
- Preflight max: 40MiB input source, 300 pages, 12MiB extracted single page. PDF password files denied. Future work: hostile PDF sandbox, scanning, memory/time limits and external object storage.
- Company access token currently checked against table rows; replace with indexed/salted principal store and SSO before enterprise launch.
- Pilot schema uses create_all; production demands migrations, encryption/key management, database-level tenant isolation, retention/consent controls and security pen-test.
- Restrict Railway staging (AGENT_UPLOADS_ENABLED=false) until controlled review. Source-only generic regression fixtures never use restricted refinery drawings.

## Railway
Use a new isolated Railway project and environment, PostgreSQL and its referenced DATABASE_URL. Set AGENT_ADMIN_TOKEN to a server-generated strong secret, AGENT_UPLOADS_ENABLED=false. Root directory /services/plant-model-service; Dockerfile in root. Health path /healthz.
Never connect the old app.main:app to the Internet for customer confidential uploads.

## Smoke test (synthetic only)
```sh
cd services/plant-model-service
python -m pip install -e '.[dev]'
python -m pytest -q tests/test_agent_pilot_gateway.py
```

## API workflow
- POST /api/admin/companies (X-Admin-Token): company_name, deployment_mode
- POST /api/projects (X-Client-Token): name
- POST /api/projects/{project_id}/documents?kind=pid&page=1 (X-Client-Token): single PDF file
- GET /api/projects/{project_id}/status (X-Client-Token): agent events, question queue, quota
- POST /api/projects/{project_id}/documents?kind=legend&page=1: missing legend resolved if recognized
- POST /api/projects/{project_id}/chat/{question_id}/reply: user's clarification
- POST /api/admin/companies/{company_id}/grant: commercial grant, admin-only

## Next integration milestone
Replace ready_for_recognition with a resumable background worker invoking existing pid_native_batch and legend library review; add engineer sign-off before any physical graph publication. Add enterprise tenant auth, data-protection gates, two-credits accounting validation on PostgreSQL, and a proper customer dashboard.

## Sprint 3 — persistent source-linked candidate-recognition agent
- `agent_pilot_gateway.py` queues a **single** durable recognition job for every quota-authorized P&ID. The gateway does not run expensive image recognition during multipart upload.
- `pid_agent_worker.py` polls the database; PostgreSQL `FOR UPDATE SKIP LOCKED` prevents concurrent double claims. A failed worker lease is retried once, then explicitly blocks for engineering review.
- Reuses the existing `pid60_pipeline.process_single_page` vector-PDF symbol-motif/CAD geometry pipeline. The output is **preliminary graphical candidates**, not the final engineering connectivity graph. Exact legend semantic class matching, OCR for raster PDFs, pump/valve identity and cross-sheet graph remain unfinished.
- Each candidate graph includes original document SHA-256, original page number, and document ID, separate from the extraction single-page PDF hash. It has zero physical engineering-approved edges by contract.
- Project-scoped tenant authentication protects GET `/api/projects/{project_id}/documents/{document_id}/candidate-graph` and `/artifact?format=png|pdf|zip`.
- `GET /api/projects/{project_id}/status` now exposes `recognition_jobs`, their state, counts, and safe error codes.
- When geometry completes, the agent asks the engineer to review sources, class labels and tee/crossings in the chat queue. Unsupported drawings (e.g., raster) create `UNSUPPORTED_DRAWING` clarification rather than fabricated CAD connections.
- `app.pid_agent_worker` runs as a **separate process/service**, configured with `AGENT_DATABASE_URL` and `AGENT_WORKER_ENABLED=true`. Only deploy in internal staging while `AGENT_UPLOADS_ENABLED=false` for external users.

### Verification and remaining limitations
Synthetic API/DB worker tests check missing legend blocking, quotas, artifact downloads and isolation; full CI also executes actual `pid60_pipeline` on a synthetic vector PDF. These synthetic tests do **not** constitute refinery recognition accuracy. PostgreSQL row-lock contention and production security require separate load/security evaluation. Large binary previews are stored temporarily inside the pilot PostgreSQL schema; switch to per-tenant encrypted object storage with retention before client rollout. Schema `create_all` must be replaced by migrations. Untrusted PDFs should be processed in resource-isolated sandbox workers with CPU/memory/page limits before public activation.
