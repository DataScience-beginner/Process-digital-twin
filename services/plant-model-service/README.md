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
