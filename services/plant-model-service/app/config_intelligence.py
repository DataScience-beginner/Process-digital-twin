"""One-node configuration intelligence vertical slice.

This module creates a fully typed pump subgraph with explicit upstream and
downstream interfaces. It NEVER claims a simulation or pipe-line binding until
an authorized source is supplied and validated.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from .models import (
    Association, Connection, ConnectionEndpoint, Equipment, EquipmentType,
    Junction, JunctionType, Nozzle, NozzleType, PlantModel,
    Port, PortDirection, PortKind,
)


class InterfaceContract(BaseModel):
    """Stable section/module-facing endpoint. Not an SVG connector."""

    name: str
    external_boundary_id: str
    external_port: str
    internal_nozzle_id: str
    internal_port: str
    direction: PortDirection
    stream_id: str | None = None
    line_id: str | None = None


class NodeAssembly(BaseModel):
    project_id: str = Field(min_length=1)
    configuration_id: str
    configuration_version: str
    primary_equipment_id: str
    graph: PlantModel
    interfaces: list[InterfaceContract]
    simulation_binding_status: str = "unbound"
    engineering_status: str = "proposed"

    @model_validator(mode="after")
    def validate_interfaces(self):
        if self.graph.project_id != self.project_id:
            raise ValueError("Project and graph IDs differ")
        if not isinstance(self.graph.object(self.primary_equipment_id), Equipment):
            raise ValueError("Primary object must be equipment")
        names = [i.name for i in self.interfaces]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate interface names")
        connections = {
            (c.source.object_id, c.source.port, c.target.object_id, c.target.port)
            for c in self.graph.connections
        }
        for interface in self.interfaces:
            boundary = self.graph.object(interface.external_boundary_id)
            nozzle = self.graph.object(interface.internal_nozzle_id)
            if not isinstance(boundary, Junction) or not isinstance(nozzle, Nozzle):
                raise ValueError("Interface must reference a boundary and a nozzle")
            if nozzle.parent_equipment_id != self.primary_equipment_id:
                raise ValueError("Interface nozzle belongs to another equipment object")
            boundary.port(interface.external_port)
            nozzle.port(interface.internal_port)
            if interface.direction == PortDirection.IN:
                edge = (boundary.id, interface.external_port, nozzle.id, interface.internal_port)
            elif interface.direction == PortDirection.OUT:
                edge = (nozzle.id, interface.internal_port, boundary.id, interface.external_port)
            else:
                raise ValueError("External interfaces require an explicit flow direction")
            if edge not in connections:
                raise ValueError(f"Missing physical connection for {interface.name}")
        return self


def build_pump_node(*, project_id: str, module_id: str, pump_tag: str) -> NodeAssembly:
    """Instantiate one approved pump node with explicit, unbound interfaces.

    This is a graph-contract pilot, NOT a complete pump installation.
    Pipe segments, valves, simulation mapping and variant assembly follow later.
    """
    if not project_id.strip() or not module_id.strip() or not pump_tag.strip():
        raise ValueError("Project, module, and tag are required")
    prefix = f"{project_id}:{module_id}"
    pump_id = f"{prefix}:PUMP"
    suction_id = f"{prefix}:SUCTION_NOZZLE"
    discharge_id = f"{prefix}:DISCHARGE_NOZZLE"
    upstream_id = f"{prefix}:UPSTREAM_BOUNDARY"
    downstream_id = f"{prefix}:DOWNSTREAM_BOUNDARY"

    pump = Equipment(
        id=pump_id, tag=pump_tag, equipment_type=EquipmentType.CENTRIFUGAL_PUMP,
        ports=[], properties={"configuration_status": "proposed"},
    )
    suction = Nozzle(
        id=suction_id, tag=f"{pump_tag}/SUC", nozzle_type=NozzleType.PROCESS,
        parent_equipment_id=pump_id,
        ports=[Port(name="PROCESS", kind=PortKind.PROCESS, direction=PortDirection.IN)],
    )
    discharge = Nozzle(
        id=discharge_id, tag=f"{pump_tag}/DIS", nozzle_type=NozzleType.PROCESS,
        parent_equipment_id=pump_id,
        ports=[Port(name="PROCESS", kind=PortKind.PROCESS, direction=PortDirection.OUT)],
    )
    upstream = Junction(
        id=upstream_id, tag=f"{pump_tag}/UPSTREAM", junction_type=JunctionType.BOUNDARY,
        ports=[Port(name="OUT", kind=PortKind.PROCESS, direction=PortDirection.OUT)],
    )
    downstream = Junction(
        id=downstream_id, tag=f"{pump_tag}/DOWNSTREAM", junction_type=JunctionType.BOUNDARY,
        ports=[Port(name="IN", kind=PortKind.PROCESS, direction=PortDirection.IN)],
    )
    graph = PlantModel(
        project_id=project_id,
        objects=[pump, suction, discharge, upstream, downstream],
        associations=[
            Association(
                id=f"{prefix}:HAS_SUCTION", subject_id=pump_id,
                relationship="has_nozzle", target_id=suction_id,
            ),
            Association(
                id=f"{prefix}:HAS_DISCHARGE", subject_id=pump_id,
                relationship="has_nozzle", target_id=discharge_id,
            ),
        ],
        connections=[
            Connection(
                id=f"{prefix}:INLET_CONNECTION",
                source=ConnectionEndpoint(object_id=upstream_id, port="OUT"),
                target=ConnectionEndpoint(object_id=suction_id, port="PROCESS"),
            ),
            Connection(
                id=f"{prefix}:OUTLET_CONNECTION",
                source=ConnectionEndpoint(object_id=discharge_id, port="PROCESS"),
                target=ConnectionEndpoint(object_id=downstream_id, port="IN"),
            ),
        ],
    )
    return NodeAssembly(
        project_id=project_id,
        configuration_id="PUMP_NODE_V1",
        configuration_version="1.0",
        primary_equipment_id=pump_id,
        graph=graph,
        interfaces=[
            InterfaceContract(
                name="upstream", external_boundary_id=upstream_id, external_port="OUT",
                internal_nozzle_id=suction_id, internal_port="PROCESS",
                direction=PortDirection.IN,
            ),
            InterfaceContract(
                name="downstream", external_boundary_id=downstream_id, external_port="IN",
                internal_nozzle_id=discharge_id, internal_port="PROCESS",
                direction=PortDirection.OUT,
            ),
        ],
    )
