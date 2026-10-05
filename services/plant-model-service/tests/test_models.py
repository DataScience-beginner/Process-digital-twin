import pytest
from pydantic import ValidationError

from app.configurations import demo_pump_installation_model
from app.models import PlantModel


def test_model_roundtrip():
    model = demo_pump_installation_model()
    restored = PlantModel.model_validate_json(model.model_dump_json())
    assert restored.project_id == model.project_id
    assert len(restored.objects) == len(model.objects)


def test_unknown_object_fails():
    data = demo_pump_installation_model().model_dump()
    data["connections"][0]["source"]["object_id"] = "UNKNOWN"
    with pytest.raises(ValidationError, match="unknown object"):
        PlantModel.model_validate(data)


def test_unknown_port_fails():
    data = demo_pump_installation_model().model_dump()
    data["connections"][0]["source"]["port"] = "NOT_A_PORT"
    with pytest.raises(ValidationError, match="unknown port"):
        PlantModel.model_validate(data)


def test_duplicate_tags_fail():
    data = demo_pump_installation_model().model_dump()
    data["objects"][1]["tag"] = data["objects"][0]["tag"]
    with pytest.raises(ValidationError, match="Duplicate object tags"):
        PlantModel.model_validate(data)
