import pytest
from pydantic import ValidationError

from app.configurations import (
    demo_vessel_pump_model,
    standard_centrifugal_pump,
    standard_vertical_separator,
)
from app.models import Connection, ConnectionEndpoint, PlantModel


def test_demo_model_is_valid():
    model = demo_vessel_pump_model()
    assert model.connections[0].source.port == "LIQUID_OUTLET"
    assert model.connections[0].target.port == "SUCTION"


def test_factories_have_expected_ports():
    vessel = standard_vertical_separator(object_id="V1", tag="V-1")
    pump = standard_centrifugal_pump(object_id="P1", tag="P-1")
    assert vessel.port("LIQUID_OUTLET").direction == "out"
    assert pump.port("SUCTION").direction == "in"


def test_unknown_port_fails():
    model = demo_vessel_pump_model().model_dump()
    model["connections"][0]["target"]["port"] = "NOT_A_PORT"
    with pytest.raises(ValidationError, match="unknown port"):
        PlantModel.model_validate(model)


def test_wrong_direction_fails():
    vessel = standard_vertical_separator(object_id="V1", tag="V-1")
    pump = standard_centrifugal_pump(object_id="P1", tag="P-1")
    with pytest.raises(ValidationError, match="source port must allow output"):
        PlantModel(
            project_id="X",
            equipment=[vessel, pump],
            connections=[
                Connection(
                    id="C1",
                    source=ConnectionEndpoint(object_id="P1", port="SUCTION"),
                    target=ConnectionEndpoint(object_id="V1", port="FEED_INLET"),
                )
            ],
        )
