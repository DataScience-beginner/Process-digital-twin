"""One-node configuration intelligence vertical slice.

This module creates a fully typed pump subgraph with explicit upstream and
downstream interfaces. It NEVER claims a simulation or pipe-line binding until
an authorized source is supplied and validated.
"""
from __future__ import annotations

from collections import deque

from pydantic import BaseModel, Field, model_validator

from .models import (
    Association, Connection, ConnectionEndpoint, Equipment, EquipmentType,
    Junction, JunctionType, Nozzle, NozzleType, PipingSegment, PlantModel,
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
    suction_segment_id: str | None = None
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
        if self.suction_segment_id is not None:
            segment = self.graph.object(self.suction_segment_id)
            if not isinstance(segment, PipingSegment):
                raise ValueError("Suction segment must be a piping segment")
            segment.port("INLET")
            segment.port("OUTLET")
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
                if self.suction_segment_id is None:
                    edge = (boundary.id, interface.external_port, nozzle.id, interface.internal_port)
                else:
                    segment_id = self.suction_segment_id
                    if (boundary.id, interface.external_port, segment_id, "INLET") not in connections:
                        raise ValueError("Missing upstream boundary to suction pipe connection")
                    edge = (segment_id, "OUTLET", nozzle.id, interface.internal_port)
            elif interface.direction == PortDirection.OUT:
                edge = (nozzle.id, interface.internal_port, boundary.id, interface.external_port)
            else:
                raise ValueError("External interfaces require an explicit flow direction")
            if edge not in connections:
                raise ValueError(f"Missing physical connection for {interface.name}")
        if self.suction_segment_id is not None and self.trace_upstream_to_downstream() != [
            self._interface("upstream").external_boundary_id,
            self.suction_segment_id,
            self._interface("upstream").internal_nozzle_id,
            self.primary_equipment_id,
            self._interface("downstream").internal_nozzle_id,
            self._interface("downstream").external_boundary_id,
        ]:
            raise ValueError("Upstream/downstream piping path is not continuous")
        return self

    def _interface(self, name: str) -> InterfaceContract:
        return next(item for item in self.interfaces if item.name == name)

    def trace_upstream_to_downstream(self) -> list[str]:
        """Trace physical process edges plus the pump internal flow transition.

        Association links are not treated as free-flow edges: only suction nozzle
        -> pump -> discharge nozzle movement is permitted for this pump contract.
        """
        start = self._interface("upstream").external_boundary_id
        end = self._interface("downstream").external_boundary_id
        adjacency: dict[str, set[str]] = {obj.id: set() for obj in self.graph.objects}
        for edge in self.graph.connections:
            if edge.kind.value == "process":
                adjacency[edge.source.object_id].add(edge.target.object_id)
        for item in self.graph.objects:
            if isinstance(item, Nozzle) and item.parent_equipment_id == self.primary_equipment_id:
                direction = item.port("PROCESS").direction
                if direction == PortDirection.IN:
                    adjacency[item.id].add(self.primary_equipment_id)
                elif direction == PortDirection.OUT:
                    adjacency[self.primary_equipment_id].add(item.id)
        pending = deque([(start, [start])])
        visited = {start}
        while pending:
            current, path = pending.popleft()
            if current == end:
                return path
            for neighbor in sorted(adjacency[current]):
                if neighbor not in visited:
                    visited.add(neighbor)
                    pending.append((neighbor, path + [neighbor]))
        return []


def build_pump_node(*, project_id: str, module_id: str, pump_tag: str) -> NodeAssembly:
    """Instantiate one approved pump node with explicit, unbound interfaces.

    This is a graph-contract pilot, NOT a complete pump installation.
    Isolation valves, simulation mapping and variant assembly follow later.
    """
    if not project_id.strip() or not module_id.strip() or not pump_tag.strip():
        raise ValueError("Project, module, and tag are required")
    prefix = f"{project_id}:{module_id}"
    pump_id = f"{prefix}:PUMP"
    suction_id = f"{prefix}:SUCTION_NOZZLE"
    discharge_id = f"{prefix}:DISCHARGE_NOZZLE"
    suction_pipe_id = f"{prefix}:SUCTION_PIPE_SEGMENT"
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
    suction_pipe = PipingSegment(
        id=suction_pipe_id, tag=f"{pump_tag}/SUCTION-PIPE", line_id=None,
        ports=[
            Port(name="INLET", kind=PortKind.PROCESS, direction=PortDirection.IN),
            Port(name="OUTLET", kind=PortKind.PROCESS, direction=PortDirection.OUT),
        ],
    )
    graph = PlantModel(
        project_id=project_id,
        objects=[pump, suction, discharge, upstream, downstream, suction_pipe],
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
                target=ConnectionEndpoint(object_id=suction_pipe_id, port="INLET"),
            ),
            Connection(
                id=f"{prefix}:SUCTION_PIPE_TO_NOZZLE",
                source=ConnectionEndpoint(object_id=suction_pipe_id, port="OUTLET"),
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
        suction_segment_id=suction_pipe_id,
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
