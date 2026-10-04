from dataclasses import dataclass

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
    PlantObjectUnion,
    Port,
    PortDirection,
    PortKind,
    Valve,
    ValveType,
)


@dataclass
class ModuleBuild:
    objects: list[PlantObjectUnion]
    connections: list[Connection]
    associations: list[Association]
    module: ModuleInstance


def p(name: str, kind: PortKind, direction: PortDirection) -> Port:
    return Port(name=name, kind=kind, direction=direction)


def ep(object_id: str, port: str) -> ConnectionEndpoint:
    return ConnectionEndpoint(object_id=object_id, port=port)


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
    ports = [p("INLET", PortKind.PROCESS, PortDirection.IN), p("OUTLET", PortKind.PROCESS, PortDirection.OUT)]
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


def transmitter(*, object_id: str, tag: str, instrument_type: InstrumentType, service: str) -> Instrument:
    return Instrument(
        id=object_id,
        tag=tag,
        instrument_type=instrument_type,
        service=service,
        ports=[p("SIGNAL_OUT", PortKind.SIGNAL, PortDirection.OUT)],
    )


def controller(*, object_id: str, tag: str, instrument_type: InstrumentType, service: str) -> Instrument:
    return Instrument(
        id=object_id,
        tag=tag,
        instrument_type=instrument_type,
        service=service,
        ports=[
            p("SIGNAL_IN", PortKind.SIGNAL, PortDirection.IN),
            p("SIGNAL_OUT", PortKind.SIGNAL, PortDirection.OUT),
        ],
    )


def standard_vessel_module(vessel: Equipment) -> ModuleBuild:
    pt = transmitter(
        object_id="INS-PT101", tag="PT-101", instrument_type=InstrumentType.PRESSURE_TRANSMITTER,
        service="Vessel pressure transmitter"
    )
    pi = Instrument(
        id="INS-PI101", tag="PI-101", instrument_type=InstrumentType.PRESSURE_INDICATOR,
        service="Vessel local pressure indication"
    )
    lt = transmitter(
        object_id="INS-LT101", tag="LT-101", instrument_type=InstrumentType.LEVEL_TRANSMITTER,
        service="Vessel level transmitter"
    )
    li = Instrument(
        id="INS-LI101", tag="LI-101", instrument_type=InstrumentType.LEVEL_INDICATOR,
        service="Vessel local level indication"
    )
    lic = controller(
        object_id="INS-LIC101", tag="LIC-101", instrument_type=InstrumentType.LEVEL_CONTROLLER,
        service="Vessel level controller"
    )
    lcv = process_valve(
        object_id="VLV-LCV101", tag="LCV-101", valve_type=ValveType.CONTROL,
        service="Vessel liquid level control"
    )
    psv = process_valve(
        object_id="VLV-PSV101", tag="PSV-101", valve_type=ValveType.RELIEF,
        service="Vessel overpressure protection"
    )
    relief_header = Junction(
        id="BOUND-RELIEF", tag="TO-RELIEF-HEADER", junction_type=JunctionType.BOUNDARY,
        service="Relief header", ports=[p("INLET", PortKind.PROCESS, PortDirection.IN)]
    )
    vent_xv = Valve(
        id="VLV-VENT101", tag="XV-VENT101", valve_type=ValveType.ISOLATION, service="Vessel vent isolation",
        ports=[
            p("INLET", PortKind.VENT, PortDirection.IN),
            p("OUTLET", PortKind.VENT, PortDirection.OUT),
        ],
    )
    drain_xv = Valve(
        id="VLV-DRAIN101", tag="XV-DRAIN101", valve_type=ValveType.ISOLATION, service="Vessel drain isolation",
        ports=[
            p("INLET", PortKind.DRAIN, PortDirection.IN),
            p("OUTLET", PortKind.DRAIN, PortDirection.OUT),
        ],
    )
    vent_boundary = Junction(
        id="BOUND-VENT", tag="TO-VENT", junction_type=JunctionType.BOUNDARY,
        service="Vent destination", ports=[p("INLET", PortKind.VENT, PortDirection.IN)]
    )
    drain_boundary = Junction(
        id="BOUND-DRAIN", tag="TO-DRAIN", junction_type=JunctionType.BOUNDARY,
        service="Closed drain", ports=[p("INLET", PortKind.DRAIN, PortDirection.IN)]
    )

    objects = [pt, pi, lt, li, lic, lcv, psv, relief_header, vent_xv, drain_xv, vent_boundary, drain_boundary]
    connections = [
        Connection(id="S-LEVEL-01", kind=ConnectionKind.SIGNAL, source=ep(lt.id, "SIGNAL_OUT"), target=ep(lic.id, "SIGNAL_IN"), service="Level signal"),
        Connection(id="S-LEVEL-02", kind=ConnectionKind.SIGNAL, source=ep(lic.id, "SIGNAL_OUT"), target=ep(lcv.id, "SIGNAL_IN"), service="Level controller output"),
        Connection(id="C-PSV-01", source=ep(vessel.id, "PSV_NOZZLE"), target=ep(psv.id, "INLET"), service="Relief inlet", logical_line="L-PSV101"),
        Connection(id="C-PSV-02", source=ep(psv.id, "OUTLET"), target=ep(relief_header.id, "INLET"), service="Relief discharge", logical_line="L-PSV101-DIS"),
        Connection(id="C-VENT-01", source=ep(vessel.id, "VENT"), target=ep(vent_xv.id, "INLET"), service="Vessel vent"),
        Connection(id="C-VENT-02", source=ep(vent_xv.id, "OUTLET"), target=ep(vent_boundary.id, "INLET"), service="Vessel vent"),
        Connection(id="C-DRAIN-01", source=ep(vessel.id, "DRAIN"), target=ep(drain_xv.id, "INLET"), service="Vessel drain"),
        Connection(id="C-DRAIN-02", source=ep(drain_xv.id, "OUTLET"), target=ep(drain_boundary.id, "INLET"), service="Vessel drain"),
    ]
    associations = [
        Association(id="A-PT101", subject_id=pt.id, relationship="measures_pressure", target_id=vessel.id),
        Association(id="A-PI101", subject_id=pi.id, relationship="indicates_pressure", target_id=vessel.id),
        Association(id="A-LT101", subject_id=lt.id, relationship="measures_level", target_id=vessel.id),
        Association(id="A-LI101", subject_id=li.id, relationship="indicates_level", target_id=vessel.id),
        Association(id="A-PSV101", subject_id=psv.id, relationship="protects", target_id=vessel.id, target_port="PSV_NOZZLE"),
    ]
    module = ModuleInstance(
        id="MOD-V101-STD",
        template="VERTICAL_SEPARATOR_STANDARD_WITH_LEVEL_CONTROL_AND_RELIEF",
        version="0.3",
        member_ids=[vessel.id, *[obj.id for obj in objects]],
    )
    return ModuleBuild(objects=objects, connections=connections, associations=associations, module=module)


def standard_pump_module(*, vessel: Equipment, liquid_control_valve: Valve) -> ModuleBuild:
    suction_xv = process_valve(
        object_id="VLV-XV101", tag="XV-101", valve_type=ValveType.ISOLATION, service="Pump suction isolation"
    )
    pump = standard_centrifugal_pump(object_id="EQ-P101", tag="P-101")
    branch = Junction(
        id="JUNC-P101-DIS", tag="J-P101-DIS", junction_type=JunctionType.BRANCH,
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
        id="BOUND-PRODUCT", tag="TO-PROCESS", junction_type=JunctionType.BOUNDARY,
        service="Downstream process", ports=[p("INLET", PortKind.PROCESS, PortDirection.IN)]
    )
    ft = Instrument(
        id="INS-FT101", tag="FT-101", instrument_type=InstrumentType.FLOW_TRANSMITTER,
        service="Minimum-flow measurement",
        ports=[
            p("INLET", PortKind.PROCESS, PortDirection.IN),
            p("OUTLET", PortKind.PROCESS, PortDirection.OUT),
            p("SIGNAL_OUT", PortKind.SIGNAL, PortDirection.OUT),
        ],
    )
    fic = controller(
        object_id="INS-FIC101", tag="FIC-101", instrument_type=InstrumentType.FLOW_CONTROLLER,
        service="Minimum-flow controller"
    )
    fcv = process_valve(
        object_id="VLV-FCV101", tag="FCV-101", valve_type=ValveType.CONTROL, service="Minimum-flow control"
    )
    pi_suction = Instrument(
        id="INS-PI101S", tag="PI-101S", instrument_type=InstrumentType.PRESSURE_INDICATOR,
        service="Pump suction pressure"
    )
    pi_discharge = Instrument(
        id="INS-PI101D", tag="PI-101D", instrument_type=InstrumentType.PRESSURE_INDICATOR,
        service="Pump discharge pressure"
    )

    objects = [suction_xv, pump, branch, nrv, discharge_xv, product, ft, fic, fcv, pi_suction, pi_discharge]
    connections = [
        Connection(id="C-LIQ-01", source=ep(vessel.id, "LIQUID_OUTLET"), target=ep(liquid_control_valve.id, "INLET"), service="Separator liquid", logical_line="L-V101-LIQ"),
        Connection(id="C-LIQ-02", source=ep(liquid_control_valve.id, "OUTLET"), target=ep(suction_xv.id, "INLET"), service="Separator liquid", logical_line="L-P101-SUC"),
        Connection(id="C-SUC-02", source=ep(suction_xv.id, "OUTLET"), target=ep(pump.id, "SUCTION"), service="Separator liquid", logical_line="L-P101-SUC"),
        Connection(id="C-DIS-01", source=ep(pump.id, "DISCHARGE"), target=ep(branch.id, "INLET"), service="Pump discharge", logical_line="L-P101-DIS"),
        Connection(id="C-DIS-02", source=ep(branch.id, "MAIN_OUT"), target=ep(nrv.id, "INLET"), service="Pump discharge", logical_line="L-P101-DIS"),
        Connection(id="C-DIS-03", source=ep(nrv.id, "OUTLET"), target=ep(discharge_xv.id, "INLET"), service="Pump discharge", logical_line="L-P101-DIS"),
        Connection(id="C-DIS-04", source=ep(discharge_xv.id, "OUTLET"), target=ep(product.id, "INLET"), service="Pump discharge", logical_line="L-P101-DIS"),
        Connection(id="C-REC-01", source=ep(branch.id, "RECYCLE_OUT"), target=ep(ft.id, "INLET"), service="Minimum-flow recycle", logical_line="L-P101-REC"),
        Connection(id="C-REC-02", source=ep(ft.id, "OUTLET"), target=ep(fcv.id, "INLET"), service="Minimum-flow recycle", logical_line="L-P101-REC"),
        Connection(id="C-REC-03", source=ep(fcv.id, "OUTLET"), target=ep(vessel.id, "RECYCLE_RETURN"), service="Minimum-flow recycle", logical_line="L-P101-REC"),
        Connection(id="S-FLOW-01", kind=ConnectionKind.SIGNAL, source=ep(ft.id, "SIGNAL_OUT"), target=ep(fic.id, "SIGNAL_IN"), service="Flow signal"),
        Connection(id="S-FLOW-02", kind=ConnectionKind.SIGNAL, source=ep(fic.id, "SIGNAL_OUT"), target=ep(fcv.id, "SIGNAL_IN"), service="Controller output"),
    ]
    associations = [
        Association(id="A-PI-SUC", subject_id=pi_suction.id, relationship="measures_pressure_at", target_id=pump.id, target_port="SUCTION"),
        Association(id="A-PI-DIS", subject_id=pi_discharge.id, relationship="measures_pressure_at", target_id=pump.id, target_port="DISCHARGE"),
    ]
    module = ModuleInstance(
        id="MOD-P101-STD",
        template="CENTRIFUGAL_PUMP_STANDARD_WITH_MIN_FLOW",
        version="0.2",
        member_ids=[obj.id for obj in objects],
    )
    return ModuleBuild(objects=objects, connections=connections, associations=associations, module=module)


def demo_pump_installation_model() -> PlantModel:
    return demo_integrated_configuration_model()


def demo_integrated_configuration_model() -> PlantModel:
    vessel = standard_vertical_separator(object_id="EQ-V101", tag="V-101")
    vessel_module = standard_vessel_module(vessel)
    lcv = next(obj for obj in vessel_module.objects if obj.id == "VLV-LCV101")
    pump_module = standard_pump_module(vessel=vessel, liquid_control_valve=lcv)

    return PlantModel(
        project_id="BDEP-DEMO-003",
        objects=[vessel, *vessel_module.objects, *pump_module.objects],
        connections=[*vessel_module.connections, *pump_module.connections],
        associations=[*vessel_module.associations, *pump_module.associations],
        modules=[vessel_module.module, pump_module.module],
    )
