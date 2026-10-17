# One-P&ID upload: fast vector evidence and provisional graph

This is a **source-neutral, Python-only MVP**. It does not contain client PDFs, glyphs, data or weights.

From `services/plant-model-service`:

```bash
python -m pip install pymupdf Pillow fastapi uvicorn python-multipart httpx
uvicorn app.pid60_web:app --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`, choose a PDF and its 1-based PDF page number, then click **Digitize P&ID**. A ZIP is returned with a full-page annotated raster preview, a zoomable vector PDF, candidate geometry graph JSON, and timing/coverage counts.

### Data model

- Whole compound instrument geometry (circle, square enclosure and horizontal divider) is recorded as a family-level candidate, preserving original vector path evidence and visible tag text.
- Long native-CAD strokes become **source geometry**; a quick endpoint-only network groups geometrically coincident endpoints but NEVER auto-confirms tees, crossing connections, flow direction or process-pipe class.
- Equipment and line-tag text is proposed with exact original PDF coordinates; associations are unverified.
- `PID_REVIEW_FILE=/approved/source_specific_review.json` is an optional local-only source-linked reviewed-evidence sidecar. Original SHA-256 and 1-based page number must match. The input review should come from a trusted project store, not arbitrary users. Accepted visual paths remain separate from approved physical pipe edges.
- `graph.edges.engineering_approved_physical_connections` is always an empty list in this prototype.

### Validation and deployment

Test: `pytest -q tests/test_pid60.py`.

Timing is recorded for extraction/render; separately measure HTTP upload/response wall time against the 60-second requirement on representative source PDFs and production hardware. Local loopback timings are not an internet or production SLA. Validated full graph generation is NOT part of the demonstrated timing. This parser is for vector CAD PDFs; it refuses raster-only scans.

**Do not deploy to the internet without organizational authentication, HTTPS, rate limiting and upload auditing.** Sources and project model outputs can be commercially confidential. Do not commit source-derived assets to public GitHub.
