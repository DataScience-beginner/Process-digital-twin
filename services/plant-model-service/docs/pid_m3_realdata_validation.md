# Digital BDEP P&ID digitization — M3 engineering validation gate

Status: **development branch only; not certified for real engineering deliverables**.

## Scope delivered in M3

- Added a source-evidenced junction decision API: an engineer may explicitly
  accept/reject an endpoint-to-interior T point; the line network is rebuilt
  from the original stroke evidence, using approved junctions only.
- Accepting a T point invalidates previously approved route proposals. A new
  process edge must be reviewed again and its direction explicitly confirmed.
- Graphic stroke provenance and approved source-tee IDs remain attached to
  resulting digital-plant connection evidence.
- The P&ID viewer displays the precise original source location and allows
  reviewed tee decisions.
- Official DEXPI 2.0 Reference P&ID benchmark script downloads both XML and
  SVG separately into a gitignored external-data directory. DEXPI XML is a
  structural semantic reference, not the output of our detector.
- Added non-network unit tests plus a supplemental GitHub Actions job testing
  the official DEXPI reference download and raster extraction.

## Public reference and licensing

- Reference: https://dexpi.org/specification/2.0/html/appendix/reference_pid.html
- License: DEXPI Specification 2.0, **CC BY 4.0**; attribution to DEXPI
  Initiative is included in exported benchmark metadata.
- Inspect newer DEXPI 2.0.1 and its reference independently:
  https://dexpi.org/specifications/
- We do not commit official drawings or third-party training data into this
  GitHub repository.

Run on an internet-enabled engineering workstation:

```bash
cd services/plant-model-service
python -m pip install -e '.[dev,ocr,vision,reference]'
# Install Tesseract executable using your OS package manager
python -m scripts.benchmark_public_dexpi --out data/pid_corpus/external/dexpi_2_0
```

The report is saved at
`data/pid_corpus/external/dexpi_2_0/dexpi_reference_report.json`.

**Important:** This report intentionally does **not** report P&ID extraction
accuracy, since DEXPI semantic object IDs are not aligned with detected visual
bounding boxes or process routes. It does report actual text-tag candidates
and graph proposals produced from the independently published SVG. Do not
equate reference XML object count with correctly recognized drawing objects.

## Definition of done for M4 (real-world capability)

Collect a permission-cleared benchmark with at least:
- 10 high-quality searchable vector P&IDs.
- 10 rasterized/scanned P&IDs from varied sources and legibility.
- 10 multi-sheet, off-page, crossed-line drawings; include intentional
  ambiguous signals, pipes, tees and reducers.
- Separate reference equipment tags, valves, instrument symbols, and
  explicitly annotated graph edges (with drawings/page/bbox).
- Document provenance, revision, drafting legend and license for every file.

Use document-level, not crop-level, train/val/test splits. Track:

| Measure | Baseline requirement |
| --- | --- |
| Tag precision/recall | Both measured separately by clean/scanned input |
| Symbol precision/recall | Per class + small-symbol subgroup |
| Graph edge precision/recall | Per sheet and cross-sheet |
| False junctions | Report absolute rate; never silently accept crossings |
| Source attribution | All published entities and edges link to original source |
| Engineer correction time | Track human minutes per drawing |
| Duplicate/outdated revisions | Verify no silent mixing of incompatible drawings |
| Security | Project isolation, authentication and malware-safe ingestion |

The recommended initial **pilot acceptance targets** (not achieved or
commercially promised) are >=95% symbol/tag recall, >=98% precision for
proposed process edges, and no silent auto-publication of an unreviewed edge.
Thresholds must be approved by the engineering discipline and differentiated
by drawing quality and criticality.

## Next engineering increments

1. Label a legally usable, diverse real-P&ID validation set.
2. Add off-page connector identity reconciliation and line-number semantics.
3. Train/evaluate a symbol model against the verified COCO-style annotations;
   keep the model interface isolated from the BDEP canonical plant model.
4. Support native CAD and DEXPI 2.x *structured import* through independent
   adapters, not via OCR of semantic XML.
5. Only after measured benchmark accuracy, implement authorized
   merge-to-baseline + engineering calculation dependencies.

## Production controls still missing

Project-scoped authorization, encryption/storage retention, virus scanning,
validated PostgreSQL schema migrations, input bounding, per-tenant quotas,
reviewer identity verification, conflict resolution and source revision
management. Do not upload confidential process-licensor drawings into the
prototype until those controls are present.
