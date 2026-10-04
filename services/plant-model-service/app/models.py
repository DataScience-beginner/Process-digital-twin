from __future__ import annotations

from enum import StrEnum
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


class Port(BaseModel):
    name: str = Field(min_length=1)
    kind: PortKind
    direction: PortDirection


class Equipment(BaseModel):
    id: str = Field(min_length=1)
    tag: str = Field(min_length=1)
    equipment_type: EquipmentType
    service: str | None = None
    ports: list[Port]
    properties: dict[str, str | float | int | bool | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_ports(self) -> "Equipment":
        names = [p.name for p in self.ports]
        if len(names) != len(set(names)):
            raise ValueError(f"Equipment {self.id} contains duplicate port names")
        return self

    def port(self, name: str) -> Port:
        for item in self.ports:
            if item.name == name:
                return item
        raise KeyError(name)


class ConnectionEndpoint(BaseModel):
    object_id: str = Field(min_length=1)
    port: str = Field(min_length=1)


class Connection(BaseModel):
    id: str = Field(min_length=1)
    source: ConnectionEndpoint
    target: ConnectionEndpoint
    service: str | None = None


class PlantModel(BaseModel):
    project_id: str = Field(min_length=1)
    equipment: list[Equipment]
    connections: list[Connection] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_graph(self) -> "PlantModel":
        ids = [e.id for e in self.equipment]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate equipment IDs are not allowed")

        tags = [e.tag for e in self.equipment]
        if len(tags) != len(set(tags)):
            raise ValueError("Duplicate equipment tags are not allowed")

        connection_ids = [c.id for c in self.connections]
        if len(connection_ids) != len(set(connection_ids)):
            raise ValueError("Duplicate connection IDs are not allowed")

        by_id = {e.id: e for e in self.equipment}
        for connection in self.connections:
            source_port = self._resolve(
                connection.id, "source", connection.source, by_id
            )
            target_port = self._resolve(
                connection.id, "target", connection.target, by_id
            )
            if source_port.direction == PortDirection.IN:
                raise ValueError(
                    f"Connection {connection.id} source port must allow output"
                )
            if target_port.direction == PortDirection.OUT:
                raise ValueError(
                    f"Connection {connection.id} target port must allow input"
                )

        return self

    @staticmethod
    def _resolve(
        connection_id: str,
        endpoint_name: str,
        endpoint: ConnectionEndpoint,
        by_id: dict[str, Equipment],
    ) -> Port:
        equipment = by_id.get(endpoint.object_id)
        if equipment is None:
            raise ValueError(
                f"Connection {connection_id} {endpoint_name} references "
                f"unknown equipment '{endpoint.object_id}'"
            )
        try:
            return equipment.port(endpoint.port)
        except KeyError:
            raise ValueError(
                f"Connection {connection_id} {endpoint_name} references "
                f"unknown port '{endpoint.port}' on equipment '{endpoint.object_id}'"
            ) from None
