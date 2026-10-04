import pytest
from pydantic import ValidationError

from app.configurations import demo_pump_installation_model
from app.models import PlantModel


def test_pump_module_builds_and_contains_expected_objects():
    model = demo_pump_installation_model()
    tags = {obj.tag for obj in model.objects}
    assert {"P-101", "XV-101", "NRV-101", "XV-102", "FT-101", "FIC-101", "FCV-101"} <= tags
    assert model.modules[0].template == "CENTRIFUGAL_PUMP_STANDARD_WITH_MIN_FLOW"


def test_minimum_flow_loop_has_process_and_signal_paths():
    model = demo_pump_installation_model()
    process = {c.id for c in model.connections if c.kind == "process"}
    signal = {c.id for c in model.connections if c.kind == "signal"}
    assert {"C-REC-01", "C-REC-02", "C-REC-03"} <= process
    assert {"S-FLOW-01", "S-FLOW-02"} <= signal


def test_pressure_indicators_associate_to_pump_ports():
    model = demo_pump_installation_model()
    links = {(a.subject_id, a.target_id, a.target_port) for a in model.associations}
    assert ("INS-PI101S", "EQ-P101", "SUCTION") in links
    assert ("INS-PI101D", "EQ-P101", "DISCHARGE") in links


def test_invalid_signal_port_is_rejected():
    data = demo_pump_installation_model().model_dump()
    for connection in data["connections"]:
        if connection["id"] == "S-FLOW-01":
            connection["source"]["port"] = "OUTLET"
    with pytest.raises(ValidationError, match="must use signal ports"):
        PlantModel.model_validate(data)
