# Refinery legend registry — complete-page coverage review workspace

The source contains 21 separate engineering legend and typical-detail sheets.
A 21-sheet page index is **not** the same as a fully validated, item-by-item
engineering symbol library. The page images and candidate records are kept in
restricted Google Drive, not in this public GitHub repository.

The generic `scripts/pid_legend_review_atlas.py` module takes a private source
PDF and a private source-hash-locked JSON registry. It renders all inventoried
pages and individual proposed symbol/description regions into an offline HTML
review workspace. No item is automatically approved. Synthetic-only tests guard
against incorrect source fingerprints, invalid source bounds, duplicate IDs and
silent approval.

## Usage (source files never committed)

```bash
cd services/plant-model-service
python -m scripts.pid_legend_review_atlas \
  --pdf /secure/client_pdf.pdf \
  --registry /secure/proposed_registry.json \
  --out /secure/client_legend_review
pytest -q tests/test_pid_legend_review_atlas.py
```

## Interpretation of status

- **Page indexed:** all source pages available to reviewer; not proof each glyph is mapped.
- **Proposed region:** source image rectangle possibly containing one glyph,
  multiple glyphs or an empty grid cell. Requires actual visual verification.
- **Owner approval:** specific source glyph-to-description pairing accepted by
  project owner, with immutable PDF hash and coordinates.
- **Independent second review:** separate required QA gate before final compiled
  client symbol library can be used as trusted recognition training material.
- **Full legend ready:** no missing symbols, no unresolved pairings, and every
  relevant page/panel signed off. No auto-promotion based on proposal count.

For Digboi sample: 21 pages are page-inventoried, 8 confirmed earlier mappings
remain owner-approved, remaining proposed regions are not approved, and the
full legend is **NOT READY**. Source drawings contain proprietary notices; use
only under appropriate authorization. Do not copy client PDF/crops/filled manifest
into public GitHub.
