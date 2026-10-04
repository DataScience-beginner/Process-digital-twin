from __future__ import annotations

from collections import deque
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class PortKind(StrEnum):
    PROCESS = "process"
    UTILITY = "utility"
    DRAIN = "drain"
    VENT = "vent"
    INSTRUMENT = "instrument"
    SIGNAL = "signal"


class PortDirection(StrEnum):
    IN = "in"
    OUT = "out"
    BIDIRECTIONAL = "bidirectional"


class EquipmentType(StrEnum):
    VERTICAL_SEPARATOR = "vertical_separator"
    CENTRIFUGAL_PUMP = "centrifugal_pump"


class ValveType(StrEnum):
    ISOLATION = "isolation_valve"
    CHECK = "check_valve"
    CONTROL = "control_valve"
    RELIEF = "relief_valve"


class InstrumentType(StrEnum):
    PRESSURE_INDICATOR = "pressure_indicator"
    PRESSURE_TRANSMITTER = "pressure_transmitter"
    LEVEL_INDICATOR = "level_indicator"
    LEVEL_TRANSMITTER = "level_transmitter"
    LEVEL_CONTROLLER = "level_controller"
    FLOW_TRANSMITTER = "flow_transmitter"
    FLOW_CONTROLLER = "flow_controller"


class JunctionType(StrEnum):
    BRANCH = "branch"
    BOUNDARY = "boundary"


class NozzleType(StrEnum):
    PROCESS = "process_nozzle"
    INSTRUMENT = "instrument_nozzle"
    ACCESS = "access_nozzle"


class ConnectionKind(StrEnum):
    PROCESS = "process"
    SIGNAL = "signal"


class Port(BaseModel):
    name: str = Field(min_length=1)
    kind: PortKind
    direction: PortDirection


class PlantObject(BaseModel):
    id: str = Field(min_length=1)
    tag: str = Field(min_length=1)
    service: str | None = None
    ports: list[Port] = Field(default_factory=list)
    properties: dict[str, str | float | int | bool | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_unique_ports(self):
        names = [port.name for port in self.ports]
        if len(names) != len(set(names)):
            raise ValueError(f"Object {self.id} contains duplicate port names")
        return self

    def port(self, name: str) -> Port:
        for port in self.ports:
            if port.name == name:
                return port
        raise KeyError(name)


class Equipment(PlantObject):
    category: Literal["equipment"] = "equipment"
    equipment_type: EquipmentType


class Valve(PlantObject):
    category: Literal["valve"] = "valve"
    valve_type: ValveType


class Instrument(PlantObject):
    category: Literal["instrument"] = "instrument"
    instrument_type: InstrumentType


class Junction(PlantObject):
    category: Literal["junction"] = "junction"
    junction_type: JunctionType


class Nozzle(PlantObject):
    category: Literal["nozzle"] = "nozzle"
    nozzle_type: NozzleType
    parent_equipment_id: str


PlantObjectUnion = Annotated[
    Equipment | Valve | Instrument | Junction | Nozzle,
    Field(discriminator="category"),
]


class ConnectionEndpoint(BaseModel):
    object_id: str = Field(min_length=1)
    port: str = Field(min_length=1)


class Connection(BaseModel):
    id: str = Field(min_length=1)
    kind: ConnectionKind = ConnectionKind.PROCESS
    source: ConnectionEndpoint
    target: ConnectionEndpoint
    service: str | None = None
    logical_line: str | None = None


class Association(BaseModel):
    id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    relationship: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    target_port: str | None = None


class ModuleInstance(BaseModel):
    id: str = Field(min_length=1)
    template: str = Field(min_length=1)
    version: str = Field(default="1.0")
    member_ids: list[str] = Field(default_factory=list)


class PlantModel(BaseModel):
    project_id: str = Field(min_length=1)
    objects: list[PlantObjectUnion]
    connections: list[Connection] = Field(default_factory=list)
    associations: list[Association] = Field(default_factory=list)
    modules: list[ModuleInstance] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_graph(self):
        object_ids = [obj.id for obj in self.objects]
        if len(object_ids) != len(set(object_ids)):
            raise ValueError("Duplicate object IDs are not allowed")

        tags = [obj.tag for obj in self.objects]
        if len(tags) != len(set(tags)):
            raise ValueError("Duplicate object tags are not allowed")

        connection_ids = [c.id for c in self.connections]
        if len(connection_ids) != len(set(connection_ids)):
            raise ValueError("Duplicate connection IDs are not allowed")

        by_id = {obj.id: obj for obj in self.objects}

        for obj in self.objects:
            if isinstance(obj, Nozzle):
                parent = by_id.get(obj.parent_equipment_id)
                if not isinstance(parent, Equipment):
                    raise ValueError(
                        f"Nozzle {obj.id} references invalid parent equipment "
                        f"'{obj.parent_equipment_id}'"
                    )

        for connection in self.connections:
            source_port = self._resolve_endpoint(connection.id, "source", connection.source, by_id)
            target_port = self._resolve_endpoint(connection.id, "target", connection.target, by_id)
            self._validate_connection_ports(connection, source_port, target_port)

        for association in self.associations:
            if association.subject_id not in by_id:
                raise ValueError(
                    f"Association {association.id} references unknown subject '{association.subject_id}'"
                )
            target = by_id.get(association.target_id)
            if target is None:
                raise ValueError(
                    f"Association {association.id} references unknown target '{association.target_id}'"
                )
            if association.target_port:
                try:
                    target.port(association.target_port)
                except KeyError:
                    raise ValueError(
                        f"Association {association.id} references unknown target port "
                        f"'{association.target_port}' on '{association.target_id}'"
                    ) from None

        for module in self.modules:
            missing = sorted(set(module.member_ids) - set(by_id))
            if missing:
                raise ValueError(
                    f"Module {module.id} references unknown members: {', '.join(missing)}"
                )

        return self

    @staticmethod
    def _resolve_endpoint(connection_id, endpoint_name, endpoint, by_id) -> Port:
        obj = by_id.get(endpoint.object_id)
        if obj is None:
            raise ValueError(
                f"Connection {connection_id} {endpoint_name} references "
                f"unknown object '{endpoint.object_id}'"
            )
        try:
            return obj.port(endpoint.port)
        except KeyError:
            raise ValueError(
                f"Connection {connection_id} {endpoint_name} references unknown port "
                f"'{endpoint.port}' on object '{endpoint.object_id}'"
            ) from None

    @staticmethod
    def _validate_connection_ports(connection: Connection, source: Port, target: Port) -> None:
        if source.direction == PortDirection.IN:
            raise ValueError(f"Connection {connection.id} source port must allow output")
        if target.direction == PortDirection.OUT:
            raise ValueError(f"Connection {connection.id} target port must allow input")

        if connection.kind == ConnectionKind.SIGNAL:
            if source.kind != PortKind.SIGNAL or target.kind != PortKind.SIGNAL:
                raise ValueError(f"Signal connection {connection.id} must use signal ports")
        elif source.kind == PortKind.SIGNAL or target.kind == PortKind.SIGNAL:
            raise ValueError(f"Process connection {connection.id} cannot use signal ports")

    def object(self, object_id: str) -> PlantObjectUnion:
        for obj in self.objects:
            if obj.id == object_id:
                return obj
        raise KeyError(object_id)

    def adjacency(self, *, include_associations: bool = True, bidirectional: bool = True) -> dict[str, set[str]]:
        graph = {obj.id: set() for obj in self.objects}

        def add_edge(source: str, target: str) -> None:
            graph[source].add(target)
            if bidirectional:
                graph[target].add(source)

        for connection in self.connections:
            add_edge(connection.source.object_id, connection.target.object_id)

        if include_associations:
            for association in self.associations:
                add_edge(association.subject_id, association.target_id)

        return graph

    def neighbors(self, object_id: str) -> set[str]:
        if object_id not in {obj.id for obj in self.objects}:
            raise KeyError(object_id)
        return self.adjacency().get(object_id, set())

    def impact_walk(self, start_id: str, *, max_depth: int | None = None) -> list[str]:
        graph = self.adjacency()
        if start_id not in graph:
            raise KeyError(start_id)

        seen = {start_id}
        queue = deque([(start_id, 0)])
        ordered: list[str] = []

        while queue:
            current, depth = queue.popleft()
            if current != start_id:
                ordered.append(current)
            if max_depth is not None and depth >= max_depth:
                continue
            for neighbor in sorted(graph[current]):
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append((neighbor, depth + 1))

        return ordered
