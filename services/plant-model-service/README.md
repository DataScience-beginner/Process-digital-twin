# Digital BDEP Plant Model Service

Python-only reference implementation for the Digital BDEP platform.

## Status

### MVP 0.1 — complete
- Pydantic canonical plant model
- Permanent object IDs separate from tags
- Explicit port-to-port connectivity
- FastAPI JSON endpoint
- Basic browser viewer

### MVP 0.2 — complete
Standard centrifugal-pump installation represented as a reusable engineering module with:
- suction isolation valve
- suction pressure indicator association
- centrifugal pump
- discharge branch
- discharge pressure indicator association
- check valve
- discharge isolation valve
- minimum-flow recycle path
- flow transmitter
- flow controller
- flow control valve
- process and signal connections
- module membership metadata

The drawing layout remains a view-layer concern; none of its coordinates are stored in the canonical plant model.

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

## Next milestone — MVP 0.3
Build the standard vessel configuration:
- PT / PI
- LT / LI / LIC
- LCV outlet control
- PSV association
- vent and drain
- vessel nozzles and control-loop semantics

Then connect the approved vessel module and pump module into one larger plant configuration.
