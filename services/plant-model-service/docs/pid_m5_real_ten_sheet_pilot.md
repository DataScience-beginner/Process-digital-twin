# M5 — Real 10-sheet P&ID engineering digitization acceptance pilot

## What is implemented

The existing project supports BOTH entry points into one downstream Digital
BDEP `PlantModel`:

- Greenfield: Process Simulation → Approved Configuration → Canonical Plant Model.
- Brownfield: Existing PDF/ZIP Client Drawing Package → Sheet Inventory →
  Legends → Source-verified symbol/line proposals → Human review →
  **Non-publishable** plant-model draft.

Open `http://localhost:8000/pid-client-intake` after installing and running
the M5 development branch. You can upload one ZIP containing 1–12 PDF files,
or upload 1–12 PDF files directly. No paid cloud services are required.

### Client-facing workflow

1. Ingest all PDF drawings, create the document register, keep SHA-256 of
   **original file**, source filename and source PDF page.
2. Automatically propose each sheet's role (drawing index, legend, P&ID,
   context, unknown); authorized engineering document control reviews roles.
3. Preview the legend pages. The model detects **text terminology**, and
   proposes nearby graphic crops. Those guesses are not training truth.
4. Drag a new bounding box around the ACTUAL source graphical symbol.
   Save that source-space rectangle with reviewer identity, then separately
   accept/reject the symbol example. Never accept without inspecting it.
5. Digitize up to 10 engineer-approved P&ID sheets from the package in one
   bounded request. A completed sheet retains an import ID, so retrying
   the package does not silently create new imports.
6. Open each generated source-linked review URL to verify tags, matched
   graphical symbols, line routes and T-junctions.
7. Export the same canonical `PlantModel` object structure as existing
   Digital BDEP, but `publish_ready=false` until engineering dependencies,
   model completeness, document revisions and security are verified.

### CLI real-data pilot (public reference only)

```bash
cd services/plant-model-service
python -m pip install -e '.[dev,ocr,vision]'
python -m scripts.collect_public_pid_sets \
  --save-originals --out data/pid_corpus/external/client_sets
python -m scripts.pilot_ten_real_pid_sheets \
  --source data/pid_corpus/external/client_sets/Pahala_WWTP_25_sheet_PIDs_with_3_legends.pdf \
  --out data/pid_corpus/external/client_sets/pilot_10 \
  --ocr-pages 12
python -m scripts.evaluate_real_pid_gold \
  --gold data/pid_corpus/external/client_sets/pilot_10/engineer_gold_annotation_tasks.json \
  --evidence data/pid_corpus/external/client_sets/pilot_10/source_candidate_evidence.json \
  --out data/pid_corpus/external/client_sets/pilot_10/accuracy_gate.json
```

Original Pāhala URL:
https://www.epa.gov/system/files/documents/2021-08/pahala-wwtp-design-build-drawings-2021-07-23.pdf

The official drawing index labels original PDF pages:
9/P-101, 10/P-201, 11/P-202, 12/P-203, 13/P-204,
14/P-205, 15/P-206, 16/P-207, 17/P-208 and 18/P-209.
The client legend sheets are original pages 6–8.

### Benchmark outcomes (GitHub CI, October 2026)

First real public 10-sheet automated pass:

| Item | Outcome |
| --- | --- |
| Real P&IDs processed | 10 |
| Machine-detected tag candidate mentions | 33 |
| Geometry-matched source symbols | 0 |
| Proposed process-graph edges | 0 |
| Independent engineer reference sheets annotated | 0 of 10 |
| Meaningful industrial precision/recall | NOT AVAILABLE |
| Baseline published or used for design | No |

These are extraction counts, NOT verified correct engineering objects.
They demonstrate the current geometry/raster methods need much more work.

### Mixed-content OCR improvement

A genuine failure mode was found: commercial CAD exports can contain native
title-block text while the actual instrumentation is embedded as an image.
The old OCR implementation skipped any page with native text, even if all
instrument bubbles were rasterized.

M5 offers opt-in local OCR over the process drawing region when the native
tag count is sparse, including tentative two-line code/loop hypotheses
(e.g. FIT above 070186), exact source PDF coordinates, and optional Tesseract
confidence. New unknown instrument types remain **unmapped**. This does NOT
constitute successful graphical symbol recognition.

For more automated extraction on a mixed PDF, check the OCR option before
the batch run. OCR is computationally costly; the initial real CI uses OCR
only on original PDF page 12. OCR is **not** required to run the other 9
reference pages, so the results reflect a mixed pipeline.

### Independent gold-label engineering process

The CLI creates an EMPTY ten-sheet human-review task bundle:
`engineer_gold_annotation_tasks.json`. Do not copy model predictions
into the gold task as accepted truth.

For each page, engineers must:
- Inspect the original PDF and check its title block and revision.
- Mark all equipment and instrument tags, with precise source rectangles.
- Mark visual symbol rectangles and their project-legend class.
- Mark process edges, branch tees and explicit off-page connectors.
- Record ambiguous/illegible symbols separately rather than guessing.
- Have **a second independent engineer** verify the completed reference.
- Set `annotation_status: independently_verified`, supply `annotator`,
  `independent_second_reviewer`, and preserve original file SHA.

The real gold evaluation tool refuses to score unreviewed pages.
Even on signed sheets it currently scores only **tag identity and undirected
connection identity**; bounding-box and line-routing precision require an
additional geometric evaluation stage.

### Production limits

This is NOT an approved client SaaS: no SSO/project-level access controls,
encryption/security policy, secure malware screening, genuine reviewer
authentication, job queue, partial-revision conflict resolution, full DEXPI
2.x import, or trained industrial vision models. The 10-sheet prototype runs
synchronously, for demonstration only; future production requires a durable
job queue with work-per-sheet, client isolation and cancellation support.

**Next technical priority:** solve real line and symbol detection using
reviewed legend examples and properly licensed industrial training drawings;
then enrich with multi-sheet connector matching and separately reviewed graph
edges. Do not enable CONVAL/downstream calculations based on this incomplete
plant model.
