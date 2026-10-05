from __future__ import annotations

from pydantic import BaseModel, Field

from .config_matcher import ConfigurationMatch, MatchStatus
from .configurations import (
    standard_centrifugal_pump,
    standard_pump_module,
    standard_vertical_separator,
    standard_vessel_module,
)
from .models import PlantModel
from .simulation import SimulationPublication


class CompilationBlocked(RuntimeError):
    pass


class ModuleExpansion(BaseModel):
    module_id: str
    created_object_ids: list[str] = Field(default_factory=list)
    created_connection_ids: list[str] = Field(default_factory=list)
    created_association_ids: list[str] = Field(default_factory=list)


class CompilationResult(BaseModel):
    configuration_id: str
    configuration_version: str
    source_simulation_case_id: str
    source_design_case_id: str
    source_design_basis_id: str
    source_design_basis_revision: str
    source_stream_to_pid_connections: dict[str, list[str]] = Field(default_factory=dict)
    module_expansions: list[ModuleExpansion] = Field(default_factory=list)
    plant_model: PlantModel


_REQUIRED_MODULES = {
    "VESSEL_LEVEL_CONTROL_01",
    "VESSEL_PRESSURE_INDICATION_01",
    "VESSEL_PROTECTION_01",
    "VESSEL_VENT_DRAIN_01",
    "PUMP_SUCTION_STANDARD_01",
    "PUMP_DISCHARGE_STANDARD_01",
    "PUMP_MIN_FLOW_STANDARD_V1",
}


def _simulation_equipment(publication: SimulationPublication, object_id: str):
    return next((item for item in publication.equipment if item.id == object_id), None)


def compile_engineering_topology(
    publication: SimulationPublication,
    match: ConfigurationMatch,
) -> CompilationResult:
    if match.status != MatchStatus.EXACT:
        raise CompilationBlocked(
            f"Engineering topology compilation requires EXACT match, got {match.status.value}."
        )
    if not match.configuration_id or not match.configuration_version:
        raise CompilationBlocked("Matched configuration identity/version is missing.")

    supplied_modules = set(match.engineering_modules)
    missing_modules = sorted(_REQUIRED_MODULES - supplied_modules)
    unknown_modules = sorted(supplied_modules - _REQUIRED_MODULES)
    if missing_modules:
        raise CompilationBlocked(
            "Approved configuration is missing required modules: "
            + ", ".join(missing_modules)
        )
    if unknown_modules:
        raise CompilationBlocked(
            "Compiler has no approved expansion implementation for modules: "
            + ", ".join(unknown_modules)
        )

    vessel_id = match.node_mapping.get("upstream_vessel")
    pump_id = match.node_mapping.get("downstream_pump")
    if not vessel_id or not pump_id:
        raise CompilationBlocked("Required node mapping is incomplete.")

    vessel_src = _simulation_equipment(publication, vessel_id)
    pump_src = _simulation_equipment(publication, pump_id)
    if vessel_src is None or pump_src is None:
        raise CompilationBlocked("Matched equipment cannot be resolved in simulation publication.")

    vessel = standard_vertical_separator(
        object_id=vessel_src.id,
        tag=vessel_src.tag,
        service=vessel_src.service,
    )
    pump = standard_centrifugal_pump(
        object_id=pump_src.id,
        tag=pump_src.tag,
        service=pump_src.service,
    )

    # The approved vessel package expands the four authorized vessel modules.
    vessel_build = standard_vessel_module(vessel)
    lcv = next(
        obj for obj in vessel_build.objects
        if obj.id == "VLV-LCV101"
    )

    # The approved pump package expands suction, discharge and minimum-flow modules.
    pump_build = standard_pump_module(
        vessel=vessel,
        liquid_control_valve=lcv,
        pump=pump,
    )

    model = PlantModel(
        project_id="BDEP-DEMO-004",
        objects=[vessel, *vessel_build.objects, *pump_build.objects],
        connections=[*vessel_build.connections, *pump_build.connections],
        associations=[*vessel_build.associations, *pump_build.associations],
        modules=[vessel_build.module, pump_build.module],
    )

    vessel_object_ids = {obj.id for obj in vessel_build.objects}
    vessel_connection_ids = {item.id for item in vessel_build.connections}
    vessel_association_ids = {item.id for item in vessel_build.associations}
    pump_object_ids = {obj.id for obj in pump_build.objects}
    pump_connection_ids = {item.id for item in pump_build.connections}
    pump_association_ids = {item.id for item in pump_build.associations}

    expansion_map = [
        ModuleExpansion(
            module_id="VESSEL_LEVEL_CONTROL_01",
            created_object_ids=sorted(
                vessel_object_ids
                & {"NOZ-V101-LT", "INS-LT101", "INS-LI101", "INS-LIC101", "VLV-LCV101"}
            ),
            created_connection_ids=sorted(
                vessel_connection_ids & {"S-LEVEL-01", "S-LEVEL-02"}
            ),
            created_association_ids=sorted(
                vessel_association_ids & {"A-LT101", "A-LI101"}
            ),
        ),
        ModuleExpansion(
            module_id="VESSEL_PRESSURE_INDICATION_01",
            created_object_ids=sorted(
                vessel_object_ids & {"NOZ-V101-PT", "INS-PT101", "INS-PI101"}
            ),
            created_association_ids=sorted(
                vessel_association_ids & {"A-PT101", "A-PI101"}
            ),
        ),
        ModuleExpansion(
            module_id="VESSEL_PROTECTION_01",
            created_object_ids=sorted(
                vessel_object_ids & {"NOZ-V101-PSV", "VLV-PSV101", "BOUND-RELIEF"}
            ),
            created_connection_ids=sorted(
                vessel_connection_ids & {"C-PSV-01", "C-PSV-02"}
            ),
            created_association_ids=sorted(
                vessel_association_ids & {"A-PSV101"}
            ),
        ),
        ModuleExpansion(
            module_id="VESSEL_VENT_DRAIN_01",
            created_object_ids=sorted(
                vessel_object_ids
                & {
                    "NOZ-V101-VENT",
                    "NOZ-V101-DRAIN",
                    "VLV-VENT101",
                    "VLV-DRAIN101",
                    "BOUND-VENT",
                    "BOUND-DRAIN",
                }
            ),
            created_connection_ids=sorted(
                vessel_connection_ids
                & {"C-VENT-01", "C-VENT-02", "C-DRAIN-01", "C-DRAIN-02"}
            ),
        ),
        ModuleExpansion(
            module_id="PUMP_SUCTION_STANDARD_01",
            created_object_ids=sorted(
                pump_object_ids & {"NOZ-P101-SUC", "VLV-XV101", "INS-PI101S"}
            ),
            created_connection_ids=sorted(
                pump_connection_ids & {"C-LIQ-01", "C-LIQ-02", "C-SUC-02"}
            ),
            created_association_ids=sorted(
                pump_association_ids & {"A-PI-SUC"}
            ),
        ),
        ModuleExpansion(
            module_id="PUMP_DISCHARGE_STANDARD_01",
            created_object_ids=sorted(
                pump_object_ids
                & {"NOZ-P101-DIS", "JUNC-P101-DIS", "VLV-NRV101", "VLV-XV102", "BOUND-PRODUCT", "INS-PI101D"}
            ),
            created_connection_ids=sorted(
                pump_connection_ids & {"C-DIS-01", "C-DIS-02", "C-DIS-03", "C-DIS-04"}
            ),
            created_association_ids=sorted(
                pump_association_ids & {"A-PI-DIS"}
            ),
        ),
        ModuleExpansion(
            module_id="PUMP_MIN_FLOW_STANDARD_V1",
            created_object_ids=sorted(
                pump_object_ids & {"INS-FT101", "INS-FIC101", "VLV-FCV101"}
            ),
            created_connection_ids=sorted(
                pump_connection_ids
                & {"C-REC-01", "C-REC-02", "C-REC-03", "S-FLOW-01", "S-FLOW-02"}
            ),
        ),
    ]

    source_stream_to_pid_connections: dict[str, list[str]] = {}
    matched_stream_id = match.stream_mapping.get("edge_0")
    if matched_stream_id:
        source_stream_to_pid_connections[matched_stream_id] = [
            "C-LIQ-01",
            "C-LIQ-02",
            "C-SUC-02",
        ]

    return CompilationResult(
        configuration_id=match.configuration_id,
        configuration_version=match.configuration_version,
        source_simulation_case_id=publication.simulation_case_id,
        source_design_case_id=publication.design_case_id,
        source_design_basis_id=publication.design_basis_id,
        source_design_basis_revision=publication.design_basis_revision,
        source_stream_to_pid_connections=source_stream_to_pid_connections,
        module_expansions=expansion_map,
        plant_model=model,
    )
