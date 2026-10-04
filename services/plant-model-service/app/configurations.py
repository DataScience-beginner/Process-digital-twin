from .models import (
    Association,
    Connection,
    ConnectionEndpoint,
    ConnectionKind,
    Equipment,
    EquipmentType,
    Instrument,
    InstrumentType,
    Junction,
    JunctionType,
    ModuleInstance,
    PlantModel,
    Port,
    PortDirection,
    PortKind,
    Valve,
    ValveType,
)


def p(name: str, kind: PortKind, direction: PortDirection) -> Port:
    return Port(name=name, kind=kind, direction=direction)


def standard_vertical_separator(*, object_id: str, tag: str, service: str = "Feed Separator") -> Equipment:
    return Equipment(
        id=object_id,
        tag=tag,
        equipment_type=EquipmentType.VERTICAL_SEPARATOR,
        service=service,
        properties={"orientation": "vertical", "status": "template-instance"},
        ports=[
            p("FEED_INLET", PortKind.PROCESS, PortDirection.IN),
            p("VAPOR_OUTLET", PortKind.PROCESS, PortDirection.OUT),
            p("LIQUID_OUTLET", PortKind.PROCESS, PortDirection.OUT),
            p("RECYCLE_RETURN", PortKind.PROCESS, PortDirection.IN),
            p("VENT", PortKind.VENT, PortDirection.OUT),
            p("DRAIN", PortKind.DRAIN, PortDirection.OUT),
            p("PSV_NOZZLE", PortKind.PROCESS, PortDirection.OUT),
        ],
    )


def standard_centrifugal_pump(*, object_id: str, tag: str, service: str = "Separator Bottoms Pump") -> Equipment:
    return Equipment(
        id=object_id,
        tag=tag,
        equipment_type=EquipmentType.CENTRIFUGAL_PUMP,
        service=service,
        properties={"driver": "motor", "status": "template-instance"},
        ports=[
            p("SUCTION", PortKind.PROCESS, PortDirection.IN),
            p("DISCHARGE", PortKind.PROCESS, PortDirection.OUT),
            p("DRAIN", PortKind.DRAIN, PortDirection.OUT),
        ],
    )


def process_valve(*, object_id: str, tag: str, valve_type: ValveType, service: str) -> Valve:
    ports = [
        p("INLET", PortKind.PROCESS, PortDirection.IN),
        p("OUTLET", PortKind.PROCESS, PortDirection.OUT),
    ]
    if valve_type == ValveType.CONTROL:
        ports.append(p("SIGNAL_IN", PortKind.SIGNAL, PortDirection.IN))
    return Valve(
        id=object_id,
        tag=tag,
        valve_type=valve_type,
        service=service,
        properties={"status": "template-instance"},
        ports=ports,
    )


def demo_pump_installation_model() -> PlantModel:
    vessel = standard_vertical_separator(object_id="EQ-V101", tag="V-101")
    suction_xv = process_valve(
        object_id="VLV-XV101", tag="XV-101", valve_type=ValveType.ISOLATION, service="Pump suction isolation"
    )
    pump = standard_centrifugal_pump(object_id="EQ-P101", tag="P-101")
    branch = Junction(
        id="JUNC-P101-DIS",
        tag="J-P101-DIS",
        junction_type=JunctionType.BRANCH,
        service="Pump discharge branch",
        ports=[
            p("INLET", PortKind.PROCESS, PortDirection.IN),
            p("MAIN_OUT", PortKind.PROCESS, PortDirection.OUT),
            p("RECYCLE_OUT", PortKind.PROCESS, PortDirection.OUT),
        ],
    )
    nrv = process_valve(
        object_id="VLV-NRV101", tag="NRV-101", valve_type=ValveType.CHECK, service="Pump discharge check"
    )
    discharge_xv = process_valve(
        object_id="VLV-XV102", tag="XV-102", valve_type=ValveType.ISOLATION, service="Pump discharge isolation"
    )
    product = Junction(
        id="BOUND-PRODUCT",
        tag="TO-PROCESS",
        junction_type=JunctionType.BOUNDARY,
        service="Downstream process",
        ports=[p("INLET", PortKind.PROCESS, PortDirection.IN)],
    )
    ft = Instrument(
        id="INS-FT101",
        tag="FT-101",
        instrument_type=InstrumentType.FLOW_TRANSMITTER,
        service="Minimum-flow measurement",
        ports=[
            p("INLET", PortKind.PROCESS, PortDirection.IN),
            p("OUTLET", PortKind.PROCESS, PortDirection.OUT),
            p("SIGNAL_OUT", PortKind.SIGNAL, PortDirection.OUT),
        ],
    )
    fic = Instrument(
        id="INS-FIC101",
        tag="FIC-101",
        instrument_type=InstrumentType.FLOW_CONTROLLER,
        service="Minimum-flow controller",
        ports=[
            p("SIGNAL_IN", PortKind.SIGNAL, PortDirection.IN),
            p("SIGNAL_OUT", PortKind.SIGNAL, PortDirection.OUT),
        ],
    )
    fcv = process_valve(
        object_id="VLV-FCV101", tag="FCV-101", valve_type=ValveType.CONTROL, service="Minimum-flow control"
    )
    pi_suction = Instrument(
        id="INS-PI101S",
        tag="PI-101S",
        instrument_type=InstrumentType.PRESSURE_INDICATOR,
        service="Pump suction pressure",
        ports=[],
    )
    pi_discharge = Instrument(
        id="INS-PI101D",
        tag="PI-101D",
        instrument_type=InstrumentType.PRESSURE_INDICATOR,
        service="Pump discharge pressure",
        ports=[],
    )

    objects = [
        vessel, suction_xv, pump, branch, nrv, discharge_xv, product,
        ft, fic, fcv, pi_suction, pi_discharge,
    ]

    connections = [
        Connection(id="C-SUC-01", source=ConnectionEndpoint(object_id=vessel.id, port="LIQUID_OUTLET"), target=ConnectionEndpoint(object_id=suction_xv.id, port="INLET"), service="Separator liquid", logical_line="L-P101-SUC"),
        Connection(id="C-SUC-02", source=ConnectionEndpoint(object_id=suction_xv.id, port="OUTLET"), target=ConnectionEndpoint(object_id=pump.id, port="SUCTION"), service="Separator liquid", logical_line="L-P101-SUC"),
        Connection(id="C-DIS-01", source=ConnectionEndpoint(object_id=pump.id, port="DISCHARGE"), target=ConnectionEndpoint(object_id=branch.id, port="INLET"), service="Pump discharge", logical_line="L-P101-DIS"),
        Connection(id="C-DIS-02", source=ConnectionEndpoint(object_id=branch.id, port="MAIN_OUT"), target=ConnectionEndpoint(object_id=nrv.id, port="INLET"), service="Pump discharge", logical_line="L-P101-DIS"),
        Connection(id="C-DIS-03", source=ConnectionEndpoint(object_id=nrv.id, port="OUTLET"), target=ConnectionEndpoint(object_id=discharge_xv.id, port="INLET"), service="Pump discharge", logical_line="L-P101-DIS"),
        Connection(id="C-DIS-04", source=ConnectionEndpoint(object_id=discharge_xv.id, port="OUTLET"), target=ConnectionEndpoint(object_id=product.id, port="INLET"), service="Pump discharge", logical_line="L-P101-DIS"),
        Connection(id="C-REC-01", source=ConnectionEndpoint(object_id=branch.id, port="RECYCLE_OUT"), target=ConnectionEndpoint(object_id=ft.id, port="INLET"), service="Minimum-flow recycle", logical_line="L-P101-REC"),
        Connection(id="C-REC-02", source=ConnectionEndpoint(object_id=ft.id, port="OUTLET"), target=ConnectionEndpoint(object_id=fcv.id, port="INLET"), service="Minimum-flow recycle", logical_line="L-P101-REC"),
        Connection(id="C-REC-03", source=ConnectionEndpoint(object_id=fcv.id, port="OUTLET"), target=ConnectionEndpoint(object_id=vessel.id, port="RECYCLE_RETURN"), service="Minimum-flow recycle", logical_line="L-P101-REC"),
        Connection(id="S-FLOW-01", kind=ConnectionKind.SIGNAL, source=ConnectionEndpoint(object_id=ft.id, port="SIGNAL_OUT"), target=ConnectionEndpoint(object_id=fic.id, port="SIGNAL_IN"), service="Flow signal"),
        Connection(id="S-FLOW-02", kind=ConnectionKind.SIGNAL, source=ConnectionEndpoint(object_id=fic.id, port="SIGNAL_OUT"), target=ConnectionEndpoint(object_id=fcv.id, port="SIGNAL_IN"), service="Controller output"),
    ]

    associations = [
        Association(id="A-PI-SUC", subject_id=pi_suction.id, relationship="measures_pressure_at", target_id=pump.id, target_port="SUCTION"),
        Association(id="A-PI-DIS", subject_id=pi_discharge.id, relationship="measures_pressure_at", target_id=pump.id, target_port="DISCHARGE"),
    ]

    module_members = [obj.id for obj in objects if obj.id != vessel.id]
    module = ModuleInstance(
        id="MOD-P101-STD",
        template="CENTRIFUGAL_PUMP_STANDARD_WITH_MIN_FLOW",
        version="0.2",
        member_ids=module_members,
    )

    return PlantModel(
        project_id="BDEP-DEMO-002",
        objects=objects,
        connections=connections,
        associations=associations,
        modules=[module],
    )
