# Digital BDEP — Legacy P&ID Digitization MVP

This first module adds the **brownfield (existing-plant) entry point** alongside
Digital BDEP's existing structured-simulation → plant-model → drawing workflow.

## Available now (technical MVP)

- Upload a **born-digital PDF** locally through the BDEP web service.
- Detect known equipment, valve and instrument tag **candidates** from vector text.
- Record page number, exact PDF-space bounding box, source string and PDF SHA-256.
- Display original source page and highlight candidate positions for human review.
- Accept/reject each candidate with reviewer ID and persisted review history.
- Produce a **disconnected, explicitly non-publishable** draft compatible with
  the existing `PlantModel` schema for supported object types.
- Retain the original PDF on the BDEP host. No external AI/cloud OCR service is called.

### Run

Install/update dependencies in the plant-model service:

```bash
cd services/plant-model-service
python -m pip install -e '.[dev]'
uvicorn app.main:app --reload --port 8000
```

Open **http://127.0.0.1:8000/pid-digitization** for upload and engineering
review. Existing Digital BDEP remains at `/engineering`.

API endpoints:

| Method | Endpoint | Usage |
| --- | --- | --- |
| POST | `/api/pid-digitization/imports` | Multipart `file` containing PDF |
| GET | `/api/pid-digitization/imports/{id}` | Extraction/review JSON |
| POST | `/api/pid-digitization/imports/{id}/review` | Reviewer and decisions |
| GET | `/api/pid-digitization/imports/{id}/pages/{page}.png` | Source page preview |
| GET | `/api/pid-digitization/imports/{id}/plant-draft` | Non-publishable PlantModel draft |

Example review body:

```json
{
  "reviewer": "instrument-engineer-01",
  "decisions": [
    {"candidate_id": "<id returned from import>", "decision": "accepted"}
  ]
}
```

Environment:

- `DATABASE_URL`: same database as the existing BDEP app.
- `BDEP_PID_STORAGE`: local directory for uploaded PDF bytes
  (default `./pid_documents`, gitignored).

Run tests: `pytest -q tests/test_pid_digitization*.py`.

## Explicit scope limits

This is **not** yet a Novek-equivalent P&ID reconstruction engine.
It deliberately **does not**:

- OCR raster-only/scanned PDF pages.
- Recognize graphic equipment symbols, drawing legends, or off-page connectors.
- Infer physical pipe/valve connectivity from vector lines.
- Match data across P&IDs, datasheets or line lists.
- Automatically update the approved plant baseline or issue deliverables.

Tag candidates are not automatically trusted. Their engineering classification
may require correction; unsupported tag types are exposed as `unmapped`.
Even accepted tags cannot be published because connectivity and attributes
remain unverified.

## Next engineering increments

1. Add OCR for raster pages with retained pixel-to-PDF source coordinates.
2. Train/configure symbol and legend recognition by P&ID standard.
3. Develop vector-line tracing and continuation/off-page connector matching.
4. Add a relation-review screen, then represent verified ports and connections.
5. Reconcile duplicate tags and contradictions across multi-sheet packages.
6. Link verified imported `PlantModel` entities to revision control and
   engineering-source provenance; add change-impact analysis.
7. Only then enable downstream process calculations and instrument sizing.

## Production gates

This prototype follows the existing BDEP demo's access model; **do not upload
confidential plant drawings to an internet-facing instance** until company SSO,
project authorization/tenant segregation, rate limits, antivirus/sandboxing,
encryption, retention/deletion policies, audit controls, and formal database
migrations have been implemented. The demo database auto-creates its table;
production PostgreSQL needs a reviewed Alembic migration.
