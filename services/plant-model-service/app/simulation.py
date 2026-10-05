from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class SimulationEquipment(BaseModel):
    id: str
    tag: str
    equipment_type: str
    service: str
    simulator_object_id: str


class SimulationStream(BaseModel):
    id: str
    simulator_stream_id: str
    stream_number: str
    source_equipment_id: str | None = None
    destination_equipment_id: str | None = None
    phase: str
    mass_flow: float
    mass_flow_unit: str = "t/h"
    temperature: float
    temperature_unit: str = "degC"
    pressure: float
    pressure_unit: str = "barg"
    density: float | None = None
    density_unit: str = "kg/m3"
    viscosity: float | None = None
    viscosity_unit: str = "cP"
    enthalpy: float | None = None
    enthalpy_unit: str = "kJ/kg"
    composition: dict[str, float] = Field(default_factory=dict)


class SimulationPublication(BaseModel):
    simulation_case_id: str
    design_case_id: str
    design_basis_id: str
    design_basis_revision: str
    simulator: str
    status: str
    equipment: list[SimulationEquipment]
    streams: list[SimulationStream]

    @model_validator(mode="after")
    def validate_topology(self):
        equipment_ids = {item.id for item in self.equipment}
        for stream in self.streams:
            if stream.source_equipment_id and stream.source_equipment_id not in equipment_ids:
                raise ValueError(f"Unknown stream source equipment {stream.source_equipment_id}")
            if stream.destination_equipment_id and stream.destination_equipment_id not in equipment_ids:
                raise ValueError(f"Unknown stream destination equipment {stream.destination_equipment_id}")
        return self

    def pfd_edges(self) -> list[dict[str, str | None]]:
        return [
            {
                "stream_id": stream.id,
                "stream_number": stream.stream_number,
                "source_equipment_id": stream.source_equipment_id,
                "destination_equipment_id": stream.destination_equipment_id,
            }
            for stream in self.streams
        ]


_CASE_DATA = {
    "CASE-NORMAL": {
        "simulation_case_id": "SIM-001",
        "feed_flow": 100.0,
        "feed_temp": 78.0,
        "feed_pressure": 4.5,
        "vapor_flow": 20.0,
        "liquid_flow": 80.0,
        "pump_discharge_pressure": 7.2,
    },
    "CASE-MAX": {
        "simulation_case_id": "SIM-002",
        "feed_flow": 115.0,
        "feed_temp": 80.0,
        "feed_pressure": 4.5,
        "vapor_flow": 23.0,
        "liquid_flow": 92.0,
        "pump_discharge_pressure": 7.5,
    },
    "CASE-TURNDOWN": {
        "simulation_case_id": "SIM-003",
        "feed_flow": 60.0,
        "feed_temp": 74.0,
        "feed_pressure": 4.4,
        "vapor_flow": 12.0,
        "liquid_flow": 48.0,
        "pump_discharge_pressure": 6.8,
    },
}


def publish_demo_simulation(design_case_id: str) -> SimulationPublication:
    try:
        data = _CASE_DATA[design_case_id]
    except KeyError:
        raise KeyError(f"Unknown design case {design_case_id}") from None

    equipment = [
        SimulationEquipment(
            id="EQ-V101",
            tag="V-101",
            equipment_type="vertical_separator",
            service="Feed Separator",
            simulator_object_id="SEP-1",
        ),
        SimulationEquipment(
            id="EQ-P101",
            tag="P-101",
            equipment_type="centrifugal_pump",
            service="Separator Bottoms Pump",
            simulator_object_id="PUMP-1",
        ),
    ]

    feed_flow = data["feed_flow"]
    vapor_flow = data["vapor_flow"]
    liquid_flow = data["liquid_flow"]

    streams = [
        SimulationStream(
            id="STR-S100",
            simulator_stream_id="S-100",
            stream_number="1100",
            destination_equipment_id="EQ-V101",
            phase="mixed",
            mass_flow=feed_flow,
            temperature=data["feed_temp"],
            pressure=data["feed_pressure"],
            density=710.0,
            viscosity=0.65,
            enthalpy=220.0,
            composition={"HC_LIGHT": 0.20, "HC_LIQUID": 0.80},
        ),
        SimulationStream(
            id="STR-S101",
            simulator_stream_id="S-101",
            stream_number="1101",
            source_equipment_id="EQ-V101",
            phase="vapor",
            mass_flow=vapor_flow,
            temperature=72.0,
            pressure=3.8,
            density=8.5,
            viscosity=0.012,
            enthalpy=390.0,
            composition={"HC_LIGHT": 0.92, "HC_LIQUID": 0.08},
        ),
        SimulationStream(
            id="STR-S102",
            simulator_stream_id="S-102",
            stream_number="1102",
            source_equipment_id="EQ-V101",
            destination_equipment_id="EQ-P101",
            phase="liquid",
            mass_flow=liquid_flow,
            temperature=72.0,
            pressure=3.8,
            density=735.0,
            viscosity=0.82,
            enthalpy=185.0,
            composition={"HC_LIGHT": 0.02, "HC_LIQUID": 0.98},
        ),
        SimulationStream(
            id="STR-S103",
            simulator_stream_id="S-103",
            stream_number="1103",
            source_equipment_id="EQ-P101",
            phase="liquid",
            mass_flow=liquid_flow,
            temperature=73.0,
            pressure=data["pump_discharge_pressure"],
            density=735.0,
            viscosity=0.82,
            enthalpy=190.0,
            composition={"HC_LIGHT": 0.02, "HC_LIQUID": 0.98},
        ),
    ]

    return SimulationPublication(
        simulation_case_id=data["simulation_case_id"],
        design_case_id=design_case_id,
        design_basis_id="DB-001",
        design_basis_revision="A",
        simulator="Digital BDEP Demo Simulator",
        status="published",
        equipment=equipment,
        streams=streams,
    )
