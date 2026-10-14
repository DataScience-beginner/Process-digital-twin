# Digital BDEP — Client P&ID digitalization pilot

Status: research/prototype. No company drawings until security approval.

## Real public packages downloaded and preflighted in CI

The M4 research downloader uses **official source URLs**, not scraped copies:

| Package | Publisher | Pages | Legends | Main purpose |
| --- | --- | --- | --- | --- |
| Pāhala Wastewater Treatment Plant | US EPA hosting / County of Hawaii | 25 | Drawings P-001/P-002/P-003, sheets 6/7/8 | Best first real client-package test |
| Virden WWTF phase 2 | Manitoba government public registry | 14 | Unknown | Scanned-image resilience |
| McKinleyville reservoir bid drawings | Local government public bid documents | 57 | P&ID legend, drawing I-01, sheet 54 | Dense mixed-discipline package |
| Los Alamos ST6999-M0002 | LANL Engineering Standards | 1 | Yes | Independent valve/instrument naming convention |

**Copyright**: Public availability ≠ permission to redistribute, copy
drawings into an open-source repository, or train a commercial AI model.
Our CI downloads the originals into its temporary worker and uploads only
derived inventory JSON. For personal/company review, download each drawing
from its original publisher after securing appropriate rights.

The collection command, run on a permission-cleared machine:

```bash
cd services/plant-model-service
python -m pip install -e '.[dev,ocr,vision]'
python -m scripts.collect_public_pid_sets \
    --out data/pid_corpus/external/client_sets \
    --save-originals --analyze-one
```

Sources, license notes, and URLs: `scripts/collect_public_pid_sets.py`.
Actual input files stay gitignored. Synthetic test files remain independently
generated and are not a measure of industrial accuracy.

## A customer's day-one workflow (implemented)

```text
Customer sends PDF drawing package (one or multiple original documents)
   |
   v
Client P&ID intake /pid-client-intake: multiple PDFs or a single ZIP
   |
   v
File preflight: PDF signature / size / page count / original SHA-256
   |
   v
Drawing register: sheet number, PDF page, index, legend, P&ID, context, unknown
   |
   v
Engineering document controller checks each sheet's role (name / review stamp)
   |
   v
Legend pass: find text labels (e.g. gate valve, instrument lines)
   |  `proposed_symbol_crop_pdf` is NOT a validated actual symbol annotation
   v
Engineer inspects source legend crop and confirms/rejects candidate examples
   |
   v
Engineer selects one classified P&ID page, clicks Analyze
   |
   v
Pipeline: text/OCR -> geometric symbols -> line strokes -> graph hypotheses
   |
   v
Source-linked result in existing /pid-digitization?import_id=... review UI
   |
   v
Engineers check each tag, visual symbol, line path, junction and direction
   |
   v
Non-publishable PlantModel draft (browfield source evidence retained)
```

### Important design rules

- A legend is a **project-specific authority**, not a list of universal
  ISA symbol assumptions. A project may contain additional vendor shapes.
- Do NOT train from a label alone; require an independently accepted
  source symbol crop. Crop geometry can be wrong and needs a reviewer.
- Do NOT use a visual spatial crossing to infer a process junction.
- Existing P&IDs may use different revisions, drawing scales or
  contradictory process equipment numbers. No automatic baseline merge.
- P&ID text extraction is only the intake stage. Actual process data,
  design criteria, hydraulic values, and equipment sizing may not be
  present on the drawings, so CONVAL cannot be reliably run from P&IDs alone.

### HTTP endpoints

- `POST /api/pid-digitization/client-batches/zip` single ZIP archive, with bounded in-memory PDF extraction\n- `POST /api/pid-digitization/client-batches` multipart
  (`client_label`, `package_label`, repeated `files`)
- `GET /api/pid-digitization/client-batches/{id}`
- `GET /api/pid-digitization/client-batches/{id}/readiness`
- `POST /api/pid-digitization/client-batches/{id}/roles/review`
- `GET /api/pid-digitization/client-batches/{id}/documents/{doc}/pages/{page}.png`
- `GET /api/pid-digitization/client-batches/{id}/documents/{doc}/legends/{term}.png`
- `POST /api/pid-digitization/client-batches/{id}/legends/review`
- `POST /api/pid-digitization/client-batches/{id}/documents/{doc}/pages/{page}/analyze`
- Existing `/api/pid-digitization/imports/{id}`, review APIs, and draft route.

### Safe limits in prototype

- Accepts multiple PDF files or a single ZIP archive of PDFs; 1–12 PDF members, <=20 MB each,
  <=70 MB combined; <=80 pages per document.
- Individual drawing pages are extracted *after* they are approved as P&ID
  and at least one legend sheet is approved as legend.
- The original full package PDF stays in local BDEP storage; source SHA,
  source original page and original document ID are propagated to reviewed
  extraction results.
- New package SQL table in demo SQLite is created on startup.
  **Production PostgreSQL requires a reviewed Alembic migration.**
- Access controls, reviewer SSO identity, antivirus, storage encryption,
  OCR sandboxing, audit integrity and retention/deletion controls remain
  mandatory production gates.

## Findings from first real public document preflight (Oct 2026)

- Pāhala 25 sheets: 3 legend pages identified; 57 source-linked
  legend term mentions; 13 pages classified outright as P&ID.
  Remaining P&ID candidates/unknowns require human classification.
- Virden 14 pages: all classified as unknown by native-text heuristics.
  This is an **expected failure for scanned/irregular drawings**, not
  evidence those pages are not P&IDs.
- McKinleyville 57 pages: its legend is detected, but the vast majority of
  other sheets remain unclassified without layout-aware understanding.
- LANL standalone legend was classified as a legend.
- Running the current graphical extraction on an actual Pāhala P&ID
  yielded **3 tag candidate mentions, zero matched symbols and zero
  connection proposals** on the chosen sheet. This is a serious
  limitation: synthetic benchmark success does not transfer to real layouts.

These are candidate/retrieval counts, not engineering precision or recall.

## Next required investment

1. Real legend layout and visual symbol pairing, with verified bounding boxes
   rather than fixed crop heuristics.
2. Extend instrument tag grammar by client-specific identification convention.
3. Trained symbol detector for small graphic shapes in densely annotated P&IDs;
   source-aligned training evidence and legal license review.
4. Process-vs-signal line/arrow/junction classification, cross-page connectors
   and drawing revision reconciliation.
5. PFD/simulation/data reconciliation and controlled baseline merge.
6. Secure multi-tenant deployments and per-client project isolation.

**Pilot acceptance gate:** no automated publication of unreviewed objects or
connections and measurable real-drawing extraction performance, not just
synthetic correctness. The first customer rollout should start as an
engineer-assisted digitization service with observable manual QA effort.
