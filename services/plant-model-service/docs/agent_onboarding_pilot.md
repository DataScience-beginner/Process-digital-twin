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
