# Digital BDEP Plant Model Service

Python-only reference implementation for the Digital BDEP platform.

## Status

### MVP 0.1 — complete
Canonical Pydantic plant model, permanent IDs, port-to-port connectivity, FastAPI JSON endpoint and basic viewer.

### MVP 0.2 — complete
Reusable centrifugal-pump installation:
- suction isolation and pressure indication
- pump
- discharge branch, NRV and isolation
- FT/FIC/FCV minimum-flow recycle
- explicit process and signal connections

### MVP 0.3 — complete
Reusable vertical-separator module connected to the pump module:
- PT / PI
- LT / LI / LIC
- LCV on vessel liquid outlet
- PSV protection + relief header
- vent isolation + vent destination
- drain isolation + closed-drain destination
- explicit level-control signal loop
- pump minimum-flow recycle returning to vessel
- two independently identified module instances in one plant model

Drawing geometry is still view-only. No coordinates are stored in the canonical engineering objects.

## Run
```bash
cd services/plant-model-service
python -m pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload --port 8765
```

Open:
- Viewer: http://127.0.0.1:8765/
- JSON model: http://127.0.0.1:8765/api/plant

## Next milestone — MVP 0.4
Replace the hard-coded drawing route/coordinates with a **data-driven renderer**:
1. symbol registry by engineering object type
2. view-model positions separated into drawing JSON
3. connection routing generated from plant connections
4. first automatic functional clustering
5. preserve the canonical model unchanged

This is the prerequisite before serious P&ID drafting intelligence.


## MVP 0.3A / 0.3B — drafting standard layer
Implemented:
- standards hierarchy documented in docs/digital-bdep/DRAFTING_STANDARDS.md
- engineering drafting TODO in docs/digital-bdep/DRAFTING_TODO.md
- DraftingProfile model
- symbol registry with declared symbol sizes and connection anchors
- monochrome engineering renderer
- process/signal/association line styles
- explicit vessel nozzles
- drawing border, zones, grid references and title block
- line identifiers and development notes
- tests requiring every current plant object to resolve to a registered symbol master

Local verification: 16/16 tests pass.

Next: qualify/refine symbol masters against the company-approved Visio stencil, then move manual view positions/routes into a DrawingView model before automatic layout.


## MVP 0.4 — semantic graph + drawing representation
Completed:
- explicit ProcessNozzle / InstrumentNozzle / AccessNozzle node types
- V-101 and P-101 connectivity routed through nozzle nodes rather than equipment geometry
- semantic graph adjacency API and impact traversal
- DrawingView / Representation / RouteRepresentation models
- every drawing shape links to semantic_object_id
- every graphical route links to semantic_edge_id
- renderer routes from symbol/nozzle anchors rather than a standalone route list
- dedicated Python CI workflow for this service

This keeps the digital thread authoritative while allowing the drafter workflow and drawing geometry to evolve independently.


## MVP 0.5A — drafter skeleton
Completed:
- staged drafter workflow model
- sheet intent / equipment / nozzle / primary piping / secondary piping / inline component / cleanup passes
- protected primary suction and discharge corridors
- separate minimum-flow recycle corridor
- hidden semantic nozzle nodes in engineering presentation
- first drawing quality gate with orthogonality and corridor checks
- dedicated engineering-skeleton endpoint at /engineering-skeleton

Python CI is green for this milestone.

Next: MVP 0.5B adds instrumentation and control loops only after the process skeleton is accepted.


## MVP 0.5C — drafter cleanup and annotation intelligence
Completed:
- typed line-tag, off-page, note and title annotations
- explicit protected drawing zones
- title block separation
- annotation overlap checks
- drawing-border bounds checks
- title-block intrusion checks
- preserved orthogonal-routing validation
- preserved 0.5A process skeleton and 0.5B instrumentation geometry

The engineering view now has a final cleanup/annotation pass before issue.
