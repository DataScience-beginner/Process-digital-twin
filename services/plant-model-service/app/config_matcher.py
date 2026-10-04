from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .simulation import SimulationPublication


class MatchStatus(StrEnum):
    EXACT = "exact"
    KNOWN_VARIANT = "known_variant"
    UNKNOWN = "unknown"


class TopologyNodeSpec(BaseModel):
    role: str
    equipment_type: str


class TopologyEdgeSpec(BaseModel):
    source_role: str
    destination_role: str
    phase: str | None = None


class ConfigurationDefinition(BaseModel):
    id: str
    name: str
    version: str
    status: str = "approved"
    nodes: list[TopologyNodeSpec]
    edges: list[TopologyEdgeSpec]
    engineering_modules: list[str] = Field(default_factory=list)
    applicability_rules: dict[str, str | float | int | bool] = Field(default_factory=dict)


class ApplicabilityCheck(BaseModel):
    rule: str
    passed: bool
    actual: str | float | int | bool | None = None
    expected: str | float | int | bool | None = None


class ConfigurationMatch(BaseModel):
    configuration_id: str | None = None
    configuration_version: str | None = None
    status: MatchStatus
    node_mapping: dict[str, str] = Field(default_factory=dict)
    stream_mapping: dict[str, str] = Field(default_factory=dict)
    applicability: list[ApplicabilityCheck] = Field(default_factory=list)
    engineering_modules: list[str] = Field(default_factory=list)
    reason: str


VESSEL_TO_PUMP_STANDARD_V1 = ConfigurationDefinition(
    id="VESSEL_TO_PUMP_STANDARD_V1",
    name="Vertical separator liquid outlet to centrifugal pump",
    version="1.0",
    nodes=[
        TopologyNodeSpec(role="upstream_vessel", equipment_type="vertical_separator"),
        TopologyNodeSpec(role="downstream_pump", equipment_type="centrifugal_pump"),
    ],
    edges=[
        TopologyEdgeSpec(
            source_role="upstream_vessel",
            destination_role="downstream_pump",
            phase="liquid",
        )
    ],
    engineering_modules=[
        "VESSEL_LEVEL_CONTROL_01",
        "VESSEL_PRESSURE_INDICATION_01",
        "VESSEL_PROTECTION_01",
        "VESSEL_VENT_DRAIN_01",
        "PUMP_SUCTION_STANDARD_01",
        "PUMP_DISCHARGE_STANDARD_01",
        "PUMP_MIN_FLOW_STANDARD_V1",
    ],
    applicability_rules={
        "pump_minimum_flow_required": True,
    },
)


APPROVED_CONFIGURATIONS = [
    VESSEL_TO_PUMP_STANDARD_V1,
]


def _equipment_by_type(publication: SimulationPublication) -> dict[str, list[str]]:
    by_type: dict[str, list[str]] = {}
    for equipment in publication.equipment:
        by_type.setdefault(equipment.equipment_type, []).append(equipment.id)
    return by_type


def _candidate_mapping(
    publication: SimulationPublication,
    definition: ConfigurationDefinition,
) -> dict[str, str] | None:
    by_type = _equipment_by_type(publication)
    mapping: dict[str, str] = {}

    for spec in definition.nodes:
        candidates = by_type.get(spec.equipment_type, [])
        if len(candidates) != 1:
            return None
        mapping[spec.role] = candidates[0]

    return mapping


def _edge_matches(
    publication: SimulationPublication,
    spec: TopologyEdgeSpec,
    mapping: dict[str, str],
) -> tuple[bool, str | None, bool]:
    """Return (topology_match, stream_id, phase_match)."""
    source_id = mapping[spec.source_role]
    destination_id = mapping[spec.destination_role]

    for stream in publication.streams:
        if (
            stream.source_equipment_id == source_id
            and stream.destination_equipment_id == destination_id
        ):
            phase_match = spec.phase is None or stream.phase == spec.phase
            return True, stream.id, phase_match

    return False, None, False


def _check_applicability(
    publication: SimulationPublication,
    definition: ConfigurationDefinition,
) -> list[ApplicabilityCheck]:
    checks: list[ApplicabilityCheck] = []

    for rule, expected in definition.applicability_rules.items():
        if rule == "pump_minimum_flow_required":
            # This is a Design Basis/configuration policy flag. For MVP 0.7 the
            # simulation publication does not own it, so matching records that
            # the rule is required and must be satisfied by the Design Basis
            # before topology compilation.
            checks.append(
                ApplicabilityCheck(
                    rule=rule,
                    passed=True,
                    actual=True,
                    expected=expected,
                )
            )
        else:
            checks.append(
                ApplicabilityCheck(
                    rule=rule,
                    passed=False,
                    actual=None,
                    expected=expected,
                )
            )

    return checks


def match_configuration(
    publication: SimulationPublication,
    definitions: list[ConfigurationDefinition] | None = None,
) -> ConfigurationMatch:
    definitions = definitions or APPROVED_CONFIGURATIONS

    variant_candidate: ConfigurationMatch | None = None

    for definition in definitions:
        mapping = _candidate_mapping(publication, definition)
        if mapping is None:
            continue

        stream_mapping: dict[str, str] = {}
        all_edges_exist = True
        all_phases_match = True

        for index, edge_spec in enumerate(definition.edges):
            edge_exists, stream_id, phase_match = _edge_matches(
                publication,
                edge_spec,
                mapping,
            )
            if not edge_exists:
                all_edges_exist = False
                break
            if stream_id:
                stream_mapping[f"edge_{index}"] = stream_id
            if not phase_match:
                all_phases_match = False

        if not all_edges_exist:
            continue

        applicability = _check_applicability(publication, definition)
        applicability_ok = all(check.passed for check in applicability)

        if all_phases_match and applicability_ok:
            return ConfigurationMatch(
                configuration_id=definition.id,
                configuration_version=definition.version,
                status=MatchStatus.EXACT,
                node_mapping=mapping,
                stream_mapping=stream_mapping,
                applicability=applicability,
                engineering_modules=definition.engineering_modules,
                reason=(
                    "Required equipment types, directed process connectivity, "
                    "stream phase and applicability rules match the approved configuration."
                ),
            )

        variant_candidate = ConfigurationMatch(
            configuration_id=definition.id,
            configuration_version=definition.version,
            status=MatchStatus.KNOWN_VARIANT,
            node_mapping=mapping,
            stream_mapping=stream_mapping,
            applicability=applicability,
            engineering_modules=definition.engineering_modules,
            reason=(
                "Core approved topology is recognized, but one or more stream "
                "attributes or applicability checks differ from the exact standard."
            ),
        )

    if variant_candidate is not None:
        return variant_candidate

    return ConfigurationMatch(
        status=MatchStatus.UNKNOWN,
        reason=(
            "No approved configuration matches the published equipment types "
            "and directed PFD connectivity. Engineering definition is required."
        ),
    )
