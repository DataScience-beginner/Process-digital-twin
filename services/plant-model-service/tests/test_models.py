import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models import PlantModel


EXAMPLE = Path(__file__).parents[1] / "examples" / "vessel_pump.json"


def load_example() -> dict:
    return json.loads(EXAMPLE.read_text())


def test_valid_vessel_to_pump_model() -> None:
    model = PlantModel.model_validate(load_example())

    assert model.project_id == "BDEP-DEMO-001"
    assert len(model.equipment) == 2
    assert model.connections[0].source.port == "LIQUID_OUTLET"
    assert model.connections[0].target.port == "SUCTION"


def test_unknown_equipment_is_rejected() -> None:
    data = load_example()
    data["connections"][0]["target"]["object_id"] = "EQ-DOES-NOT-EXIST"

    with pytest.raises(ValidationError, match="unknown equipment"):
        PlantModel.model_validate(data)


def test_unknown_port_is_rejected() -> None:
    data = load_example()
    data["connections"][0]["target"]["port"] = "WRONG_PORT"

    with pytest.raises(ValidationError, match="unknown port"):
        PlantModel.model_validate(data)


def test_duplicate_tags_are_rejected() -> None:
    data = load_example()
    data["equipment"][1]["tag"] = "V-101"

    with pytest.raises(ValidationError, match="Duplicate equipment tags"):
        PlantModel.model_validate(data)
