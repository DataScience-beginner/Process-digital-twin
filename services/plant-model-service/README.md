# Digital BDEP Plant Model Service

Python-only reference implementation for the Digital BDEP platform.

## MVP 0.1
- Pydantic canonical plant model
- Standard vertical-separator factory
- Standard centrifugal-pump factory
- Explicit port-to-port connectivity
- Validation of unknown equipment, unknown ports and connection direction
- FastAPI endpoint exposing the plant model as JSON
- Small clickable HTML/SVG concept viewer

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

## Architecture rule
The plant model is the engineering master. Drawing coordinates and layout are view data only and must not be added to the canonical equipment/connectivity model.
