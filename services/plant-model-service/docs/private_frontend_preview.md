# Digital BDEP — private visual frontend preview

A **separate, password-gated, synthetic-only frontend** for the existing P&ID agent platform. It is not a customer portal and does not touch existing refinery documents, the agent gateway, the recognition worker, or PostgreSQL.

## What the internal reviewer can explore

- Overview with the agent sequence, simulated pilot quota, and review status.
- Client onboarding and a scripted **missing legend → clarification → sample legend** interaction.
- Interactive P&ID canvas with synthetic vector drawing, candidate overlays, object category selection, zoom and a right-hand Process / Connections / Review inspector.
- Engineering graph view; deliberately **zero approved piping edges**.
- Illustrative engineering register and sample CSV export.
- Review queue with simulated decisions and a scripted chat assistant.
- Privacy and learning policy matrix (managed / dedicated / private cloud).

**All data is synthetic.** It performs no file upload, API request, inference, real client lookup, or real engineering graph publication.

## Local run

```bash
cd services/plant-model-service
export PREVIEW_ACCESS_PASSWORD='replace-with-strong-unique-password'
export PREVIEW_SESSION_KEY='replace-with-different-32-plus-character-secret'
export PORT=8000
python -m app.preview_frontend
# Open http://localhost:8000
```

The frontend server requires a 16+ character password and a separate 32+ character session HMAC secret. It serves only four allowlisted paths (HTML/CSS/JS and health) and requires a signed, HttpOnly, Secure, SameSite cookie for all UI assets. `/healthz` is accessible for Railway health checks and contains only a static status. The login is rate-limitable at Railway's edge; enterprise production auth/SSO is still required.

## Railway isolated staging deployment

Create an additional service in existing **PID-Agent-Digitalization / staging** from the existing GitHub repo and `feature/pid-private-frontend-preview` branch.

- Root directory: `/services/plant-model-service`
- Dockerfile: `Dockerfile` (already used by the gateway and worker)
- Custom start command: `python -m app.preview_frontend`
- Healthcheck path: `/healthz`
- Variables: `PREVIEW_ACCESS_PASSWORD`, `PREVIEW_SESSION_KEY`, `PORT=8000` (never commit secrets)
- Public domain: optional for previewing on a phone or browser; **password must be set first**. Keep customer uploads disabled on separate backend services.

Prefer isolating this UI as a separate service so the existing gateway's API surface, credentials and deployments remain unchanged. For a true localhost-only preview, do not create a Railway public domain and use local instructions instead.

## Explicit limitations

- Preview controls are interactive, but scripted; their state is client-side and resets on reload.
- Does not consume free P&ID credits or submit commercial contact requests.
- Data shown in dashboard, legend, tags and graph is synthetic rather than retrieved from the database.
- Backend agent orchestration and actual recognition live in separate Railway staging services, and are **not connected to this UI**.
- Requires production identity/RBAC, tenant isolation, rate limits, audit trail and full P&ID review integration before inviting clients or enabling real uploads.