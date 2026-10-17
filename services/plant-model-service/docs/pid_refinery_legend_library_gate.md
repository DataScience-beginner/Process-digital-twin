# Legend-first digitization gate (M2 reset)

**Why this exists:** previous exploratory extracts stopped at 22 symbols from one sheet; some P&ID matches were false positives. Do not resume full-drawing symbol detection until the client legend itself is complete and source-reviewed.

## GitHub versus customer data

- **GitHub source of truth:** `DataScience-beginner/Process-digital-twin`, `services/plant-model-service/`.
- **Only generic code, documentation, synthetic tests, and non-client fixtures** may be committed to this PUBLIC repository.
- Original refinery PDFs, glyph images, extracted text, filled manifests, and sensitive engineering outputs stay in the customer's authorized **private Google Drive**. Do not commit source-derived data.
- Previous one-shot experiments remain benchmarks only; NOT approved symbols or piping relationships.

## Correct processing order

1. **Inventory all legend sheets**: some project packages contain many legend pages, including typical details instead of individual symbols. An engineer checks sheet identity and relevant groups.
2. **Pair each glyph with its actual adjacent description**: the manifest stores `glyph_bbox_pdf_pt`, `label_bbox_pdf_pt`, `label_verbatim`, source SHA, page number and proposed class. A glyph without the label is not a class.
3. **Review every entry separately**: inspect full source context, verify crop isolation, resolve multiple glyph variants under the same descriptive term, and record distinct graphic reviewer and description reviewer. Proposed classifications may not be approved automatically.
4. **Completeness per page**: engineer records `expected_symbol_items` and `reviewed_complete`. Abbreviation and notes-only sheets may have `expected_symbol_items=0` only after actual inspection. Unfinished pages keep full library in `NOT_READY` state.
5. **Compile private library**: run program and save private glyph + description proof pairs and a JSON review queue. `approved.json` excludes all candidates without dual human review.
6. **Only then** test symbol recognition on independent P&IDs and report independently measured precision/recall. Engineering ports, direction, and connectivity each need independent validation gates.

```bash
cd services/plant-model-service
python -m scripts.build_pid_legend_library inventory \
  --pdf /private/client.pdf --legend-pages 3-8 --out /private/client-library
# Review/edit the manifest in /private/client-library/inventory.json
python -m scripts.build_pid_legend_library compile \
  --pdf /private/client.pdf \
  --manifest /private/client-library/inventory.json \
  --out /private/client-library/build
pytest -q tests/test_pid_legend_library.py
```

### Optional raw ink-row proposals — NOT mapped library entries

After identifying the actual graphical-symbol and text columns on a source sheet,
run the uncalibrated column segmentation helper. Requires optional `vision`
dependencies: `pip install -e '.[dev,vision]'`. Every exported proposed row has
an empty label and is not a valid reviewed symbol; some bands merge two glyphs.

```bash
python -m scripts.build_pid_legend_library propose-rows --pdf /private/client.pdf \
  --page 4 --glyph-x 210,238 --label-x 245,335 --y 40,700 \
  --prefix COL_A --out /private/client-library
# Safely append the proposals to inventory.json, inspect pairs and correct boxes.
python -m scripts.build_pid_legend_review_html \
  --manifest /private/client-library/inventory.json \
  --compiled-dir /private/client-library/build \
  --out /private/client-library/engineer_review.html
```

The offline reviewer merely exports metadata, without authentication. Any
engineering approval must be verified outside this prototype. An 'approved'
value in a JSON file is not an authenticated signoff.

### Manifest entry example (SYNTHETIC; no client-derived coordinates)

```json
{
  "id": "TEST_VALVE_01", "page_1based": 1,
  "glyph_bbox_pdf_pt": [30,35,105,95],
  "label_bbox_pdf_pt": [130,48,390,82],
  "label_verbatim": "SYNTHETIC VALVE - normally open",
  "class_code": "valve_open", "review_status": "needs_review",
  "ports_review_status": "UNVERIFIED"
}
```

To move an entry to `approved`, both `glyph_isolated_confirmed` and `label_paired_confirmed` must be true; `glyph_reviewer` and `label_reviewer` must be distinct named engineers. Neither template score nor an LLM's inference is a substitute.

**Current honest status:** code-level first library gate implemented; full client sheet-by-sheet glyph mapping and independent engineering review are NOT complete. No P&ID recognition accuracy or engineering connectivity has been validated.
