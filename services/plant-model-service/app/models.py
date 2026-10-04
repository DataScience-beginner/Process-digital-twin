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

    @model_validator(mode="after")
    def validate_unique_ports(self) -> "Equipment":
        names = [port.name for port in self.ports]
        if len(names) != len(set(names)):
            raise ValueError(f"Equipment {self.id} contains duplicate port names")
        return self


class ConnectionEndpoint(BaseModel):
    object_id: str = Field(min_length=1)
    port: str = Field(min_length=1)


class Connection(BaseModel):
    id: str = Field(min_length=1)
    source: ConnectionEndpoint
    target: ConnectionEndpoint


class PlantModel(BaseModel):
    project_id: str = Field(min_length=1)
    equipment: list[Equipment]
    connections: list[Connection] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_graph(self) -> "PlantModel":
        equipment_ids = [item.id for item in self.equipment]
        if len(equipment_ids) != len(set(equipment_ids)):
            raise ValueError("Duplicate equipment IDs are not allowed")

        tags = [item.tag for item in self.equipment]
        if len(tags) != len(set(tags)):
            raise ValueError("Duplicate equipment tags are not allowed")

        connection_ids = [item.id for item in self.connections]
        if len(connection_ids) != len(set(connection_ids)):
            raise ValueError("Duplicate connection IDs are not allowed")

        equipment_by_id = {item.id: item for item in self.equipment}

        for connection in self.connections:
            self._validate_endpoint(
                connection_id=connection.id,
                endpoint_name="source",
                endpoint=connection.source,
                equipment_by_id=equipment_by_id,
            )
            self._validate_endpoint(
                connection_id=connection.id,
                endpoint_name="target",
                endpoint=connection.target,
                equipment_by_id=equipment_by_id,
            )

        return self

    @staticmethod
    def _validate_endpoint(
        *,
        connection_id: str,
        endpoint_name: str,
        endpoint: ConnectionEndpoint,
        equipment_by_id: dict[str, Equipment],
    ) -> None:
        equipment = equipment_by_id.get(endpoint.object_id)
        if equipment is None:
            raise ValueError(
                f"Connection {connection_id} {endpoint_name} references "
                f"unknown equipment '{endpoint.object_id}'"
            )

        valid_ports = {port.name for port in equipment.ports}
        if endpoint.port not in valid_ports:
            raise ValueError(
                f"Connection {connection_id} {endpoint_name} references "
                f"unknown port '{endpoint.port}' on equipment '{endpoint.object_id}'"
            )
