from __future__ import annotations

from pydantic import BaseModel, Field


class DraftingProfile(BaseModel):
    name: str = "BDEP_PID_BASELINE"
    sheet_width: int = 1180
    sheet_height: int = 760
    margin: int = 28
    title_block_height: int = 82
    notes_zone_width: int = 190
    equipment_stroke: float = 1.6
    piping_stroke: float = 1.5
    signal_stroke: float = 1.1
    instrument_diameter: int = 28
    tag_font_size: int = 11
    annotation_font_size: int = 8
    min_clearance: int = 16
    grid_columns: int = 8
    grid_rows: int = 5


class SymbolMaster(BaseModel):
    key: str
    width: int
    height: int
    anchors: dict[str, tuple[float, float]] = Field(default_factory=dict)


STANDARD_PROFILE = DraftingProfile()

SYMBOLS: dict[str, SymbolMaster] = {
    "equipment.vertical_separator": SymbolMaster(
        key="equipment.vertical_separator",
        width=72,
        height=170,
        anchors={},
    ),
    "equipment.centrifugal_pump": SymbolMaster(
        key="equipment.centrifugal_pump",
        width=58,
        height=52,
        anchors={},
    ),
    "nozzle.process_nozzle": SymbolMaster(
        key="nozzle.process_nozzle",
        width=8,
        height=8,
        anchors={"CONNECTION": (0.5, 0.5)},
    ),
    "nozzle.instrument_nozzle": SymbolMaster(
        key="nozzle.instrument_nozzle",
        width=8,
        height=8,
        anchors={"CONNECTION": (0.5, 0.5)},
    ),
    "nozzle.access_nozzle": SymbolMaster(
        key="nozzle.access_nozzle",
        width=8,
        height=8,
        anchors={"CONNECTION": (0.5, 0.5)},
    ),
    "valve.isolation_valve": SymbolMaster(
        key="valve.isolation_valve",
        width=34,
        height=22,
        anchors={"INLET": (0.0, 0.5), "OUTLET": (1.0, 0.5)},
    ),
    "valve.check_valve": SymbolMaster(
        key="valve.check_valve",
        width=34,
        height=22,
        anchors={"INLET": (0.0, 0.5), "OUTLET": (1.0, 0.5)},
    ),
    "valve.control_valve": SymbolMaster(
        key="valve.control_valve",
        width=38,
        height=42,
        anchors={
            "INLET": (0.0, 0.65),
            "OUTLET": (1.0, 0.65),
            "SIGNAL_IN": (0.5, 0.0),
        },
    ),
    "valve.relief_valve": SymbolMaster(
        key="valve.relief_valve",
        width=34,
        height=42,
        anchors={"INLET": (0.5, 1.0), "OUTLET": (0.5, 0.0)},
    ),
    "instrument.bubble": SymbolMaster(
        key="instrument.bubble",
        width=28,
        height=28,
        anchors={
            "SIGNAL_IN": (0.5, 0.0),
            "SIGNAL_OUT": (0.5, 1.0),
        },
    ),
    "instrument.flow_transmitter_inline": SymbolMaster(
        key="instrument.flow_transmitter_inline",
        width=34,
        height=34,
        anchors={
            "INLET": (0.0, 0.5),
            "OUTLET": (1.0, 0.5),
            "SIGNAL_OUT": (0.5, 0.0),
        },
    ),
    "junction.branch": SymbolMaster(
        key="junction.branch",
        width=8,
        height=8,
        anchors={
            "INLET": (0.0, 0.5),
            "MAIN_OUT": (1.0, 0.5),
            "RECYCLE_OUT": (0.5, 0.0),
        },
    ),
    "junction.boundary": SymbolMaster(
        key="junction.boundary",
        width=28,
        height=16,
        anchors={"INLET": (0.0, 0.5), "OUTLET": (1.0, 0.5)},
    ),
}


def symbol_key(obj) -> str:
    if obj.category == "equipment":
        return f"equipment.{obj.equipment_type.value}"
    if obj.category == "nozzle":
        return f"nozzle.{obj.nozzle_type.value}"
    if obj.category == "valve":
        return f"valve.{obj.valve_type.value}"
    if obj.category == "instrument":
        if (
            obj.instrument_type.value == "flow_transmitter"
            and any(port.name == "INLET" for port in obj.ports)
        ):
            return "instrument.flow_transmitter_inline"
        return "instrument.bubble"
    if obj.category == "junction":
        return f"junction.{obj.junction_type.value}"
    raise KeyError(f"No symbol mapping for category {obj.category!r}")


def master_for(obj) -> SymbolMaster:
    key = symbol_key(obj)
    try:
        return SYMBOLS[key]
    except KeyError:
        raise KeyError(f"No symbol master registered for {key}") from None
