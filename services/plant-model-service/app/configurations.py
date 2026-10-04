from .models import (
    Connection,
    ConnectionEndpoint,
    Equipment,
    EquipmentType,
    PlantModel,
    Port,
    PortDirection,
    PortKind,
)


def standard_vertical_separator(
    *, object_id: str, tag: str, service: str = "Feed Separator"
) -> Equipment:
    return Equipment(
        id=object_id,
        tag=tag,
        equipment_type=EquipmentType.VERTICAL_SEPARATOR,
        service=service,
        properties={"orientation": "vertical", "status": "template-instance"},
        ports=[
            Port(name="FEED_INLET", kind=PortKind.PROCESS, direction=PortDirection.IN),
            Port(name="VAPOR_OUTLET", kind=PortKind.PROCESS, direction=PortDirection.OUT),
            Port(name="LIQUID_OUTLET", kind=PortKind.PROCESS, direction=PortDirection.OUT),
            Port(name="VENT", kind=PortKind.VENT, direction=PortDirection.OUT),
            Port(name="DRAIN", kind=PortKind.DRAIN, direction=PortDirection.OUT),
            Port(name="PSV_NOZZLE", kind=PortKind.PROCESS, direction=PortDirection.OUT),
        ],
    )


def standard_centrifugal_pump(
    *, object_id: str, tag: str, service: str = "Separator Bottoms Pump"
) -> Equipment:
    return Equipment(
        id=object_id,
        tag=tag,
        equipment_type=EquipmentType.CENTRIFUGAL_PUMP,
        service=service,
        properties={"driver": "motor", "status": "template-instance"},
        ports=[
            Port(name="SUCTION", kind=PortKind.PROCESS, direction=PortDirection.IN),
            Port(name="DISCHARGE", kind=PortKind.PROCESS, direction=PortDirection.OUT),
            Port(name="DRAIN", kind=PortKind.DRAIN, direction=PortDirection.OUT),
        ],
    )


def demo_vessel_pump_model() -> PlantModel:
    vessel = standard_vertical_separator(object_id="EQ-000001", tag="V-101")
    pump = standard_centrifugal_pump(object_id="EQ-000002", tag="P-101")
    return PlantModel(
        project_id="BDEP-DEMO-001",
        equipment=[vessel, pump],
        connections=[
            Connection(
                id="CONN-000001",
                service="Separator liquid",
                source=ConnectionEndpoint(object_id=vessel.id, port="LIQUID_OUTLET"),
                target=ConnectionEndpoint(object_id=pump.id, port="SUCTION"),
            )
        ],
    )
