# P&ID adaptive symbol learning: controlled MVP

**Status:** the repository contains an exploratory nearest-exemplar shape model and synthetic tests. It does not contain refinery drawings or trained refinery model weights.

## Architecture

- Source-anchored legend registry: image, caption, original PDF coordinates, source SHA, client namespace, reviewer decisions.
- Canonical engineering concepts: preserve distinctions between normally-open and normally-closed valves, signal vs process connections, and symbol classes vs composite hookup details.
- Versioned recognition: a generic HOG/shape baseline produces candidate labels or UNKNOWN. Every prediction is unverified and graph edges are never implicitly accepted.
- Correction loop: an engineer's accepted/rejected or corrected prediction is quarantined. It becomes a training sample only after independent review, training-rights clearance, and deliberate versioned retraining.
- Evaluation: require an independent real P&ID document-level holdout and class-wise measurements before claiming precision, recall or deploying.

## Restrictions

The private Digboi refinery owner-approved mappings are stored in the connected project Drive, not in public GitHub. Approval of legend text/picture pairings does not grant permission to train on third-party drawings or establish connectivity. All source images, feedback and fitted client models remain client-isolated and access-controlled.

## Synthetic test

```sh
cd services/plant-model-service
python -m pip install -e '.[dev,vision]'
python -m pytest -q tests/test_pid_symbol_learning.py
```

A versioned learning proof was tested using only generated synthetic glyphs: 2 concept classes in version 1 and 3 classes in version 2. Neither result establishes actual refinery recognition quality.

## Next engineering gate

Obtain authorization for model training on the real engineering drawings, arrange second-review of individual glyphs, capture engineer-reviewed P&ID symbol bounding boxes, then train client-specific baseline and measure precision/coverage against a wholly held-out drawing. Only afterward integrate approved topology into the Fulton-style graph loop.
