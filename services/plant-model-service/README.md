# Plant Model Service

Python/Pydantic reference implementation of the canonical Digital BDEP plant model.

## Why a separate service?
The repository already has a .NET equipment microservice. This service is intentionally small and domain-focused so the canonical process-engineering model can be proven before choosing the final persistence/API integration pattern.

## Run tests
```bash
cd services/plant-model-service
python -m pip install -e ".[dev]"
pytest
```

## Validate the example
```bash
python - <<'PY'
from pathlib import Path
from app.models import PlantModel

model = PlantModel.model_validate_json(
    Path("examples/vessel_pump.json").read_text()
)
print(model.model_dump_json(indent=2))
PY
```
