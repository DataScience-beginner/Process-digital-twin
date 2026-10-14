# Digital BDEP — Brownfield P&ID digitization pipeline

Status: **engineering prototype, test-gated with synthetic fixtures; not validated on real industrial drawings**.
This module is deliberately separate from greenfield simulation → plant-model compilation.

## 1. Input corpus (ready to generate)

A rights-aware dataset registry is committed at:
`data/pid_corpus/catalog.json`.

Locally generate six original forms and an explicit reference graph:

```bash
cd services/plant-model-service
python -m pip install -e '.[dev,ocr,vision]'
python scripts/generate_pid_corpus.py
```

Generated inputs (gitignored):
- `baseline.pdf`: clean born-digital PDF with linework and native text.
- `complex.pdf`: vectors, signal lines crossing process lines without a junction.
- `multisheet.pdf`: two-page drawing.
- `elbow_crossing.pdf`: multi-stroke piping bends with deliberate non-junction solid crossing.\n- `scanned.pdf`: image-only PDF (no native PDF text).
- `raster.png`: lossless raster.
- `compressed.jpg`: lossy raster.
- `expected_graph.json`: manually defined synthetic ground truth (not an inference input).

The catalog additionally points to DEXPI public example cases, DLR PID2Graph
(GraphML), Digitize-PID (YOLO) and PIDQA (graph question answering). These
external datasets are **not downloaded or bundled**, because their drawing-level
license and commercial reuse terms vary.

## 2. End-to-end pipeline status

```text
Local PDF / PNG / JPG upload
   ↓ normalize to private source PDF + SHA-256 + coordinate conversion
PDF text & bounding boxes ────────→ Optional local Tesseract OCR
   ↓                                       ↓
PDF vector primitive extraction      Raster OpenCV contours/Hough lines
   └───────────────────┬───────────────────┘
                       ↓
            Source-linked tag candidates
                       ↓
       Geometric symbol hypotheses (circle, rect, bow-tie triangles)
                       ↓
        Multi-segment endpoint graph (no crossing junctions), each stroke ID retained
                       ↓
             Engineering review, including process direction
                       ↓
  Reviewed-tag / explicitly approved-edge Digital BDEP PlantModel draft
                       ↓
      Future: approved engineering baseline + DEXPI interchange
```

**Implemented:** Input normalization, vector text, optional local OCR,
vector and raster geometry heuristics, candidate symbol tagging,
conservative multi-stroke endpoint topology proposals, full-route source highlighting, persisted
tag/link review and export of explicitly approved process connections into a
schema-valid draft PlantModel. This is a real staged workflow but *not* robust
industrial P&ID understanding.

**Not implemented:** Trained symbol model, native DWG/DXF parsing, DEXPI 2.0
import, endpoint-on-interior T junctions and junction dots, off-page connector matching,
automatic signal-versus-process line classification, advanced topology checks
or publication into the approved plant baseline.

**Design rule:** Never convert geometric proximity or OCR confidence into an
approved instrument/pipeline relationship without engineering review.
Crossings are not automatically junctions. Unverified line direction is never
assumed to be process flow direction.

## 3. How to run

```bash
cd services/plant-model-service
python -m pip install -e '.[dev,ocr,vision]'
uvicorn app.main:app --reload --port 8000
```

Tesseract binary must be installed separately and available on PATH for OCR.
If optional packages/binary are absent, the relevant stage gives a warning
instead of silently manufacturing results.

Open **http://127.0.0.1:8000/pid-digitization**.

The user:
1. Uploads PDF, PNG or JPEG. Chooses local OCR when scanning/raster input.
2. Reviews extracted text tag candidates against the original page.
3. Independently reviews visual symbol matches (tag recognition is not symbol verification).\n4. Reviews complete source-highlighted multi-stroke connection suggestions.
5. Explicitly selects accepted/rejected and approved process direction.\n6. Opens the Digital BDEP `PlantModel` draft and evidence references.

API endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/pid-digitization/imports?ocr=true` | Multipart upload; typed source normalization |
| GET | `/api/pid-digitization/imports/{id}` | Source, normalized stages, tags, geometry |
| GET | `/api/pid-digitization/imports/{id}/evidence` | Machine-readable source evidence, symbol/link hypotheses |
| GET | `/api/pid-digitization/imports/{id}/pages/{page}.png` | Source page preview |
| POST | `/api/pid-digitization/imports/{id}/review` | Human review of tag candidates |
| POST | `/api/pid-digitization/imports/{id}/symbols/review` | Human review of visual geometry hypotheses (independent of tag review) |\n| POST | `/api/pid-digitization/imports/{id}/connections/review` | Human review of traced line proposals and process direction |\n| GET | `/api/pid-digitization/imports/{id}/annotations` | Reviewed source-aligned COCO-style symbol annotations |
| GET | `/api/pid-digitization/imports/{id}/plant-draft` | Reviewed PlantModel draft, publish_ready=false |

Example connection-review request:

```json
{
  "reviewer": "process-engineer-1",
  "decisions": [
    {"proposal_id": "<id from import>", "decision": "accepted", "direction": "a_to_b"}
  ]
}
```

The directed edge is inserted only if both tag identities were already accepted
and the proposal was classified as an eligible process-line connection.
Instrument tap candidates are recorded as evidence but require additional
typed-port engineering rules before graph publication.

## 4. Evidence contract

Every tag has `id`, canonical `tag`, `page`, original `bbox` (PDF
points, top-left origin), `source_text`, `source_method`, `review_status`.
Each image-origin import retains original file SHA-256 and pixel-to-PDF
transform, while the normalized PDF has its own SHA-256.

Each source-derived connection carries `tag_a`, `tag_b`,
`source_segment_ids`, full `source_route_points`, `source_bbox`, `page`, `direction`,
`review_status` and (once approved) reviewer details.

Source evidence is preserved in the import record. The exported draft contains
`edge_source_evidence` keyed to the resulting PlantModel connection IDs.

## 5. Benchmark plan

Assess each dataset separately:
- OCR tag accuracy/recall, including duplicate-tag handling.
- Symbol precision/recall by discipline and input modality.
- Connection proposal precision/recall versus verified ground truth.
- False-junction rates at crossings and off-page connectors.
- Source-page and bounding-box provenance completeness.
- Engineer correction effort per sheet, and final graph validity.

Use synthetic fixtures for deterministic regressions and reserve external
real-drawing datasets as independent tests. Partition by original drawing
rather than patches to prevent train/test leakage.

Run smoke tests (full updated application still requires CI):

```bash
pytest -q tests/test_pid_digitization.py \
  tests/test_pid_digitization_api.py tests/test_pid_full_pipeline.py
```

## 6. Deployment and licensing gates

This module inherits the current BDEP prototype's demo access model. **Never
upload confidential company drawings to a public or shared BDEP instance.**
Before production add SSO, project-level access controls, storage encryption,
malware protection, safe parsing/rate limits, audit and retention controls,
Alembic migrations for the new import table and workload limits.

Do not automatically redistribute/download third-party sources without
per-drawing license checks. In particular, a common Digitize-PID derivative
is labelled research-only; pyDEXPI is AGPL-3.0 (commercial licensing check
needed before embedding in a proprietary product).

The next focused milestone is trained symbol detection + polyline network
tracing with manually confirmed multi-sheet graph links, then controlled
publishing into the BDEP revision baseline.


## M2 implementation and benchmark

M2 replaces single-stroke graph proposals with per-page endpoint-snapped graph
search. Bends comprising multiple disjoint PDF strokes can now be traversed
through exact or near-exact endpoint joins; the route stops at each detected
symbol so an FCV does not collapse into the upstream/downstream line.

Vector dashed strokes are excluded from process networks. Crossings where both
lines pass through an interior point are not joined. T branches with an endpoint\non the interior of another line are now detected as **unresolved tee evidence**\nwith exact source positions but are not inserted into the process graph.\nUnverified off-sheet connectors remain an open engineering challenge. No flow direction is inferred.

Each connection proposal retains an ordered `source_route_points` polyline
and ordered `source_segment_ids`. The source review UI can highlight the
entire traced line on the original drawing. Even a perfect geometric match
is **not a verified process connection** until engineer review.

Tag review and geometric symbol verification are now separate operations.
Only symbols explicitly accepted by an engineer (and with accepted tags)\ncan appear in the COCO-style training-annotation API. A tag-only PDF does not\ngenerate positive visual training labels.

### Automated benchmark report

```bash
cd services/plant-model-service
python -m scripts.benchmark_pid_extraction
cat data/pid_corpus/benchmark_report.json
```

This reports precision/recall/F1 for tags, shapes and undirected process
connection hypotheses on independent synthetic fixtures, plus source-evidence
completeness. The CI job also archives its benchmark JSON as an artifact.
These values are *synthetic acceptance checks only*, not claims of industrial
generalization. Real/PID2Graph dataset evaluation is next.

M2 is on branch `feature/pid-topology-graph-m2` in draft PR #5.
