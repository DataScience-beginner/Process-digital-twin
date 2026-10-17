# Source-traceable P&ID markup proposals (M3 foundation)

This adds **evidence extraction only** to the Brownfield/P&ID workflow. It accepts a `fitz.Page` and returns observed text candidates (equipment/loop codes), isolated long horizontal/vertical red CAD stroke candidates, and a fail-closed preliminary graph with **zero accepted nodes or connections**. The requester must review source glyphs, line types, tee/crossing decisions, off-page connectors, instrument signal lines, and graph endpoints before publication.

`pytest -q services/plant-model-service/tests/test_pid_text_review.py`

Synthetic tests check that text does not become an approved node, crossings do not become connections, and loop-code proximity is explicitly an unreviewed hypothesis. No restricted client PDFs/images or approval records are committed to GitHub. The private Digboi first-P&ID markup and reviewer are retained in the client's connected Drive workspace.

## Planned next steps

- Link source glyphs to the project-owner-approved legend records (client-specific data remains private).
- Extend reviewer to approve/reject physical symbol bboxes, not just text occurrences.
- Detect route strokes by line style and distinguish literal CAD strokes from connected runs.
- Review tees/crossings and construct graph edges from explicitly approved endpoints only.
- Then validate against independently labeled full drawing sheets; never claim industrial accuracy from unreviewed candidates.
