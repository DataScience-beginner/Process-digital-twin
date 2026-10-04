from __future__ import annotations

import math
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config_matcher import MatchStatus, match_configuration
from .db_schema import (
    DesignBasisCriterionRow,
    DesignBasisRevisionRow,
    EngineeringRecordRow,
    PublicationStageRow,
    RecordObjectLinkRow,
    SimulationCaseRow,
)
from .persistence import (
    PROJECT_ID,
    load_approved_configurations,
    load_configuration_match_facts,
)
from .simulation import publish_demo_simulation
from .thread_models import RecordDomain


class PublishStage(StrEnum):
    DESIGN_BASIS = "design_basis"
    SIMULATION = "simulation"
    CONFIGURATION = "configuration"
    PROCESS = "process"
    INSTRUMENTATION = "instrumentation"
    MECHANICAL = "mechanical"
    COSTING = "costing"


STAGE_ORDER = [
    PublishStage.DESIGN_BASIS,
    PublishStage.SIMULATION,
    PublishStage.CONFIGURATION,
    PublishStage.PROCESS,
    PublishStage.INSTRUMENTATION,
    PublishStage.MECHANICAL,
    PublishStage.COSTING,
]

STAGE_DEPENDENCIES: dict[PublishStage, list[PublishStage]] = {
    PublishStage.DESIGN_BASIS: [],
    PublishStage.SIMULATION: [PublishStage.DESIGN_BASIS],
    PublishStage.CONFIGURATION: [PublishStage.SIMULATION],
    PublishStage.PROCESS: [PublishStage.CONFIGURATION],
    PublishStage.INSTRUMENTATION: [PublishStage.PROCESS],
    PublishStage.MECHANICAL: [PublishStage.PROCESS],
    PublishStage.COSTING: [PublishStage.INSTRUMENTATION, PublishStage.MECHANICAL],
}


class PublicationStatus(BaseModel):
    stage: PublishStage
    label: str
    status: str
    revision: str | None = None
    published_at: str | None = None
    dependencies: list[PublishStage] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class PublicationResult(BaseModel):
    stage: PublishStage
    status: str
    revision: str
    summary: dict[str, Any] = Field(default_factory=dict)
    records_written: list[str] = Field(default_factory=list)


class PublicationBlocked(RuntimeError):
    pass


_STAGE_LABELS = {
    PublishStage.DESIGN_BASIS: "Design Basis",
    PublishStage.SIMULATION: "Simulation",
    PublishStage.CONFIGURATION: "Configuration",
    PublishStage.PROCESS: "Process / Safety",
    PublishStage.INSTRUMENTATION: "Instrumentation / DCS",
    PublishStage.MECHANICAL: "Mechanical",
    PublishStage.COSTING: "Costing",
}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _criterion(session: Session, criterion_id: str) -> Any:
    row = session.get(DesignBasisCriterionRow, criterion_id)
    if row is None:
        raise PublicationBlocked(f"Missing Design Basis criterion: {criterion_id}")
    if row.status != "approved":
        raise PublicationBlocked(
            f"Design Basis criterion {criterion_id} is not approved."
        )
    return row.value_json


def _stage_row(session: Session, stage: PublishStage) -> PublicationStageRow | None:
    return session.scalar(
        select(PublicationStageRow).where(
            PublicationStageRow.project_id == PROJECT_ID,
            PublicationStageRow.stage == stage.value,
        )
    )


def _require_dependencies(session: Session, stage: PublishStage) -> None:
    missing = []
    for dependency in STAGE_DEPENDENCIES[stage]:
        row = _stage_row(session, dependency)
        if row is None or row.status != "published":
            missing.append(dependency.value)
    if missing:
        raise PublicationBlocked(
            f"{stage.value} publication requires published stages: "
            + ", ".join(missing)
        )


def _set_stage(
    session: Session,
    *,
    stage: PublishStage,
    summary: dict[str, Any],
    revision: str = "A",
) -> PublicationResult:
    row = _stage_row(session, stage)
    if row is None:
        row = PublicationStageRow(
            id=f"{PROJECT_ID}:{stage.value}",
            project_id=PROJECT_ID,
            stage=stage.value,
            revision=revision,
            status="published",
            published_at=_now(),
            summary_json=summary,
            provenance_json={
                "source_type": "digital_bdep_publisher",
                "source_id": f"PUBLISH-{stage.value.upper()}",
                "source_revision": revision,
            },
        )
        session.add(row)
    else:
        row.revision = revision
        row.status = "published"
        row.published_at = _now()
        row.summary_json = summary
        row.provenance_json = {
            "source_type": "digital_bdep_publisher",
            "source_id": f"PUBLISH-{stage.value.upper()}",
            "source_revision": revision,
        }
    return PublicationResult(
        stage=stage,
        status="published",
        revision=revision,
        summary=summary,
    )


def _upsert_record(
    session: Session,
    *,
    record_id: str,
    domain: RecordDomain,
    name: str,
    value: Any,
    unit: str | None,
    status: str,
    source_id: str,
    method: str,
    object_ids: list[str],
    metadata: dict[str, Any] | None = None,
) -> str:
    provenance = {
        "source_type": "deterministic_service",
        "source_id": source_id,
        "source_revision": "A",
        "method": method,
    }
    row = session.get(EngineeringRecordRow, record_id)
    if row is None:
        row = EngineeringRecordRow(
            id=record_id,
            project_id=PROJECT_ID,
            domain=domain.value,
            name=name,
            value_json=value,
            unit=unit,
            status=status,
            provenance_json=provenance,
            metadata_json=metadata or {},
        )
        session.add(row)
    else:
        row.domain = domain.value
        row.name = name
        row.value_json = value
        row.unit = unit
        row.status = status
        row.provenance_json = provenance
        row.metadata_json = metadata or {}

    session.flush()
    existing_links = {
        link.object_id
        for link in session.scalars(
            select(RecordObjectLinkRow).where(
                RecordObjectLinkRow.engineering_record_id == record_id
            )
        ).all()
    }
    for object_id in object_ids:
        if object_id not in existing_links:
            session.add(
                RecordObjectLinkRow(
                    engineering_record_id=record_id,
                    object_id=object_id,
                    relationship="applies_to",
                )
            )
    return record_id


def publication_status(session: Session) -> list[PublicationStatus]:
    rows = {
        row.stage: row
        for row in session.scalars(
            select(PublicationStageRow).where(
                PublicationStageRow.project_id == PROJECT_ID
            )
        ).all()
    }
    result = []
    for stage in STAGE_ORDER:
        row = rows.get(stage.value)
        result.append(
            PublicationStatus(
                stage=stage,
                label=_STAGE_LABELS[stage],
                status=row.status if row else "not_published",
                revision=row.revision if row else None,
                published_at=(
                    row.published_at.isoformat() if row and row.published_at else None
                ),
                dependencies=STAGE_DEPENDENCIES[stage],
                summary=row.summary_json if row else {},
            )
        )
    return result


def publish_design_basis(session: Session) -> PublicationResult:
    revision = session.get(DesignBasisRevisionRow, "DB-001-A")
    if revision is None or revision.status != "approved":
        raise PublicationBlocked("Approved Design Basis DB-001 Rev A is required.")
    count = len(
        session.scalars(
            select(DesignBasisCriterionRow).where(
                DesignBasisCriterionRow.design_basis_revision_id == "DB-001-A",
                DesignBasisCriterionRow.status == "approved",
            )
        ).all()
    )
    result = _set_stage(
        session,
        stage=PublishStage.DESIGN_BASIS,
        summary={
            "design_basis_id": "DB-001",
            "revision": "A",
            "approved_criteria": count,
        },
    )
    session.commit()
    return result


def publish_simulation(session: Session) -> PublicationResult:
    _require_dependencies(session, PublishStage.SIMULATION)
    cases = session.scalars(select(SimulationCaseRow)).all()
    expected = {"SIM-001", "SIM-002", "SIM-003"}
    available = {case.id for case in cases}
    if not expected <= available:
        raise PublicationBlocked("Normal, Maximum and Turndown simulations are required.")
    result = _set_stage(
        session,
        stage=PublishStage.SIMULATION,
        summary={
            "cases": ["SIM-001", "SIM-002", "SIM-003"],
            "case_types": ["normal", "maximum", "turndown"],
            "topology": "V-101 -> S-102 -> P-101",
        },
    )
    session.commit()
    return result


def publish_configuration(session: Session) -> PublicationResult:
    _require_dependencies(session, PublishStage.CONFIGURATION)
    publication = publish_demo_simulation("CASE-NORMAL")
    match = match_configuration(
        publication,
        design_basis_facts=load_configuration_match_facts(session),
        definitions=load_approved_configurations(session),
    )
    if match.status != MatchStatus.EXACT:
        raise PublicationBlocked(
            f"Configuration selection requires EXACT match; got {match.status.value}."
        )
    result = _set_stage(
        session,
        stage=PublishStage.CONFIGURATION,
        summary={
            "configuration_id": match.configuration_id,
            "configuration_version": match.configuration_version,
            "match_status": match.status.value,
            "modules": match.engineering_modules,
        },
    )
    session.commit()
    return result


def _process_numbers(session: Session) -> dict[str, float]:
    maximum = publish_demo_simulation("CASE-MAX")
    normal = publish_demo_simulation("CASE-NORMAL")
    max_liquid = next(s for s in maximum.streams if s.id == "STR-S102")
    normal_liquid = next(s for s in normal.streams if s.id == "STR-S102")

    vessel_margin = float(_criterion(session, "DBC-VESSEL-SIZING-MARGIN")) / 100.0
    holdup_minutes = float(_criterion(session, "DBC-VESSEL-HOLDUP"))
    pump_flow_margin = float(_criterion(session, "DBC-PUMP-FLOW-MARGIN")) / 100.0
    pump_head_margin = float(_criterion(session, "DBC-PUMP-HEAD-MARGIN")) / 100.0
    pump_efficiency = float(_criterion(session, "DBC-PUMP-EFFICIENCY")) / 100.0
    motor_margin = float(_criterion(session, "DBC-MOTOR-MARGIN")) / 100.0

    vessel_design_flow_tph = max_liquid.mass_flow * (1.0 + vessel_margin)
    volumetric_m3h = vessel_design_flow_tph * 1000.0 / float(max_liquid.density)
    holdup_volume_m3 = volumetric_m3h * holdup_minutes / 60.0

    rated_flow_tph = max_liquid.mass_flow * (1.0 + pump_flow_margin)
    dp_bar = maximum.streams[-1].pressure - max_liquid.pressure
    raw_head_m = dp_bar * 100000.0 / (float(max_liquid.density) * 9.80665)
    rated_head_m = raw_head_m * (1.0 + pump_head_margin)
    q_m3s = rated_flow_tph * 1000.0 / float(max_liquid.density) / 3600.0
    hydraulic_kw = (
        float(max_liquid.density) * 9.80665 * q_m3s * rated_head_m / 1000.0
    )
    shaft_kw = hydraulic_kw / pump_efficiency
    motor_kw = shaft_kw * (1.0 + motor_margin)

    return {
        "max_liquid_flow_tph": max_liquid.mass_flow,
        "normal_liquid_flow_tph": normal_liquid.mass_flow,
        "liquid_density_kgm3": float(max_liquid.density),
        "vessel_design_flow_tph": vessel_design_flow_tph,
        "holdup_volume_m3": holdup_volume_m3,
        "pump_rated_flow_tph": rated_flow_tph,
        "pump_rated_head_m": rated_head_m,
        "pump_shaft_kw": shaft_kw,
        "motor_preliminary_kw": motor_kw,
    }


_STANDARD_NPS_IN = [1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0]


def _stream_case_table(stream_id: str) -> list[dict[str, Any]]:
    rows = []
    for design_case_id, label in [
        ("CASE-NORMAL", "Normal"),
        ("CASE-MAX", "Maximum"),
        ("CASE-TURNDOWN", "Turndown"),
    ]:
        publication = publish_demo_simulation(design_case_id)
        stream = next(item for item in publication.streams if item.id == stream_id)
        rows.append(
            {
                "case": label,
                "design_case_id": design_case_id,
                "simulation_case_id": publication.simulation_case_id,
                "stream_number": stream.stream_number,
                "mass_flow_tph": float(stream.mass_flow),
                "pressure_barg": float(stream.pressure),
                "temperature_degC": float(stream.temperature),
                "density_kgm3": float(stream.density) if stream.density is not None else None,
            }
        )
    return rows


def _select_nps(flow_tph: float, density_kgm3: float, max_velocity_ms: float) -> dict[str, float]:
    q_m3s = flow_tph * 1000.0 / density_kgm3 / 3600.0
    required_d_m = math.sqrt(4.0 * q_m3s / (math.pi * max_velocity_ms))
    required_in = required_d_m / 0.0254
    selected = next((size for size in _STANDARD_NPS_IN if size >= required_in), _STANDARD_NPS_IN[-1])
    selected_d_m = selected * 0.0254
    selected_area = math.pi * selected_d_m**2 / 4.0
    selected_velocity = q_m3s / selected_area
    return {
        "flow_m3s": q_m3s,
        "required_diameter_m": required_d_m,
        "required_diameter_in": required_in,
        "selected_nps_in": selected,
        "selected_velocity_ms": selected_velocity,
    }


def _velocity_for_case(flow_tph: float, density_kgm3: float, nps_in: float) -> float:
    q_m3s = flow_tph * 1000.0 / density_kgm3 / 3600.0
    diameter_m = nps_in * 0.0254
    area = math.pi * diameter_m**2 / 4.0
    return q_m3s / area


def _line_number(
    *,
    nps_in: float,
    fluid_code: str,
    sequence: str,
    piping_class: str,
) -> str:
    size_text = str(int(nps_in)) if float(nps_in).is_integer() else str(nps_in)
    return f'{size_text}"-{fluid_code}-{sequence}-{piping_class}'


def _line_sizing_records(session: Session, n: dict[str, float]) -> list[dict[str, Any]]:
    fluid_code = str(_criterion(session, "DBC-LINE-FLUID-CODE"))
    piping_class = str(_criterion(session, "DBC-LINE-PIPING-CLASS"))
    suction_limit = float(_criterion(session, "DBC-LINE-SUCTION-VEL"))
    discharge_limit = float(_criterion(session, "DBC-LINE-DISCHARGE-VEL"))
    recycle_limit = float(_criterion(session, "DBC-LINE-RECYCLE-VEL"))

    max_case = publish_demo_simulation("CASE-MAX")
    max_liquid = next(item for item in max_case.streams if item.id == "STR-S102")
    density = float(max_liquid.density)

    suction = _select_nps(max_liquid.mass_flow, density, suction_limit)
    discharge = _select_nps(max_liquid.mass_flow, density, discharge_limit)

    min_flow_fraction = float(_criterion(session, "DBC-PUMP-MIN-FLOW-FRACTION")) / 100.0
    recycle_design_tph = n["pump_rated_flow_tph"] * min_flow_fraction
    recycle = _select_nps(recycle_design_tph, density, recycle_limit)

    case_rows = _stream_case_table("STR-S102")
    suction_cases = [
        {
            **row,
            "velocity_ms": round(
                _velocity_for_case(row["mass_flow_tph"], row["density_kgm3"], suction["selected_nps_in"]),
                3,
            ),
        }
        for row in case_rows
    ]
    discharge_cases = [
        {
            **row,
            "velocity_ms": round(
                _velocity_for_case(row["mass_flow_tph"], row["density_kgm3"], discharge["selected_nps_in"]),
                3,
            ),
        }
        for row in case_rows
    ]
    recycle_cases = [
        {
            **row,
            "required_recycle_tph": round(max(recycle_design_tph - row["mass_flow_tph"], 0.0), 3),
            "velocity_ms": round(
                _velocity_for_case(
                    max(recycle_design_tph - row["mass_flow_tph"], 0.0),
                    row["density_kgm3"],
                    recycle["selected_nps_in"],
                ),
                3,
            ),
        }
        for row in case_rows
    ]

    return [
        {
            "record_id": "LINE-1102-SIZING",
            "service": "V-101 liquid outlet / P-101 suction",
            "stream_number": "1102",
            "simulator_stream_id": "S-102",
            "sequence": "1102",
            "line_number": _line_number(
                nps_in=suction["selected_nps_in"],
                fluid_code=fluid_code,
                sequence="1102",
                piping_class=piping_class,
            ),
            "criterion_velocity_ms": suction_limit,
            "selected_nps_in": suction["selected_nps_in"],
            "required_diameter_in": suction["required_diameter_in"],
            "design_velocity_ms": suction["selected_velocity_ms"],
            "case_results": suction_cases,
            "object_ids": ["EQ-V101", "EQ-P101"],
            "governing_case": "Maximum",
            "governing_reason": "Maximum case has the highest published liquid flow in stream 1102.",
        },
        {
            "record_id": "LINE-1103-SIZING",
            "service": "P-101 discharge to downstream process",
            "stream_number": "1103",
            "simulator_stream_id": "S-103",
            "sequence": "1103",
            "line_number": _line_number(
                nps_in=discharge["selected_nps_in"],
                fluid_code=fluid_code,
                sequence="1103",
                piping_class=piping_class,
            ),
            "criterion_velocity_ms": discharge_limit,
            "selected_nps_in": discharge["selected_nps_in"],
            "required_diameter_in": discharge["required_diameter_in"],
            "design_velocity_ms": discharge["selected_velocity_ms"],
            "case_results": discharge_cases,
            "object_ids": ["EQ-P101"],
            "governing_case": "Maximum",
            "governing_reason": "Maximum case has the highest published pump discharge flow.",
        },
        {
            "record_id": "LINE-1190-SIZING",
            "service": "P-101 minimum-flow recycle to V-101",
            "stream_number": None,
            "simulator_stream_id": None,
            "sequence": "1190",
            "line_number": _line_number(
                nps_in=recycle["selected_nps_in"],
                fluid_code=fluid_code,
                sequence="1190",
                piping_class=piping_class,
            ),
            "criterion_velocity_ms": recycle_limit,
            "selected_nps_in": recycle["selected_nps_in"],
            "required_diameter_in": recycle["required_diameter_in"],
            "design_velocity_ms": recycle["selected_velocity_ms"],
            "design_flow_tph": recycle_design_tph,
            "case_results": recycle_cases,
            "object_ids": ["EQ-P101", "VLV-FCV101", "EQ-V101"],
            "governing_case": "Minimum-flow design case",
            "governing_reason": "Recycle line is sized for the minimum-flow protection duty rather than the normal process stream flow.",
        },
    ]


def _calculation_detail(
    *,
    inputs: list[dict[str, Any]],
    criteria: list[dict[str, Any]],
    case_results: list[dict[str, Any]],
    governing_case: str,
    governing_reason: str,
    outputs: list[dict[str, Any]],
    method: str,
) -> dict[str, Any]:
    return {
        "calculation_detail": {
            "inputs": inputs,
            "criteria": criteria,
            "case_results": case_results,
            "governing_case": governing_case,
            "governing_reason": governing_reason,
            "outputs": outputs,
            "method": method,
        }
    }


def publish_process(session: Session) -> PublicationResult:
    _require_dependencies(session, PublishStage.PROCESS)
    n = _process_numbers(session)
    record_ids = []

    record_ids.append(
        _upsert_record(
            session,
            record_id="CALC-V101-HOLDUP",
            domain=RecordDomain.PROCESS_CALC,
            name="Vessel preliminary liquid holdup sizing",
            value={
                "governing_case": "SIM-002 / Maximum",
                "maximum_liquid_flow_tph": round(n["max_liquid_flow_tph"], 3),
                "design_liquid_flow_tph": round(n["vessel_design_flow_tph"], 3),
                "required_holdup_volume_m3": round(n["holdup_volume_m3"], 3),
            },
            unit=None,
            status="process_checked_demo",
            source_id="CALC-V101-HOLDUP",
            method="max liquid flow × vessel margin; volumetric flow × holdup time",
            object_ids=["EQ-V101"],
        )
    )
    record_ids.append(
        _upsert_record(
            session,
            record_id="CALC-P101-RATED-FLOW",
            domain=RecordDomain.PROCESS_CALC,
            name="Pump preliminary rated duty",
            value={
                "governing_case": "SIM-002 / Maximum",
                "rated_flow_tph": round(n["pump_rated_flow_tph"], 3),
                "rated_head_m": round(n["pump_rated_head_m"], 3),
                "shaft_power_kw": round(n["pump_shaft_kw"], 3),
                "preliminary_motor_kw": round(n["motor_preliminary_kw"], 3),
            },
            unit=None,
            status="process_checked_demo",
            source_id="CALC-P101-001",
            method="maximum simulated duty + Design Basis margins",
            object_ids=["EQ-P101"],
        )
    )

    psv_set = float(_criterion(session, "DBC-PSV-SET-PRESSURE"))
    accumulation = float(_criterion(session, "DBC-PSV-ACCUMULATION"))
    maximum = publish_demo_simulation("CASE-MAX")
    feed = next(s for s in maximum.streams if s.id == "STR-S100")
    record_ids.append(
        _upsert_record(
            session,
            record_id="RELIEF-PSV101-BASIS",
            domain=RecordDomain.PROCESS_CALC,
            name="PSV preliminary relief basis",
            value={
                "governing_scenario": "Blocked outlet / demo screening case",
                "set_pressure_barg": psv_set,
                "accumulation_allowance_pct": accumulation,
                "preliminary_relief_load_tph": feed.mass_flow,
                "final_orifice_area": "TBD - qualified relief sizing service required",
            },
            unit=None,
            status="relief_basis_ready_demo",
            source_id="RELIEF-PSV101-001",
            method="structured relief-basis publisher; no AI orifice sizing",
            object_ids=["EQ-V101", "VLV-PSV101"],
            metadata={"safety_critical": True, "qualified_service_required": True},
        )
    )

    result = _set_stage(
        session,
        stage=PublishStage.PROCESS,
        summary={
            "records": record_ids,
            "vessel_holdup_volume_m3": round(n["holdup_volume_m3"], 3),
            "pump_rated_flow_tph": round(n["pump_rated_flow_tph"], 3),
            "pump_rated_head_m": round(n["pump_rated_head_m"], 3),
            "psv_basis": "published; final relief sizing service pending qualification",
        },
    )
    result.records_written = record_ids
    session.commit()
    return result


def publish_instrumentation(session: Session) -> PublicationResult:
    _require_dependencies(session, PublishStage.INSTRUMENTATION)
    n = _process_numbers(session)
    min_flow_fraction = float(_criterion(session, "DBC-PUMP-MIN-FLOW-FRACTION")) / 100.0
    cv_dp = float(_criterion(session, "DBC-CV-SIZING-DP"))
    cv_margin = float(_criterion(session, "DBC-CV-SIZING-MARGIN")) / 100.0
    fail_position = str(_criterion(session, "DBC-CV-FAIL-FCV101"))
    normal_opening = float(_criterion(session, "DBC-CV-NORMAL-OPENING"))
    max_opening = float(_criterion(session, "DBC-CV-MAX-OPENING"))
    signal_standard = str(_criterion(session, "DBC-DCS-SIGNAL-STANDARD"))

    min_flow_tph = n["pump_rated_flow_tph"] * min_flow_fraction
    q_m3h = min_flow_tph * 1000.0 / n["liquid_density_kgm3"]
    sg = n["liquid_density_kgm3"] / 1000.0
    kv = q_m3h * math.sqrt(sg / cv_dp)
    raw_cv = 1.156 * kv
    design_cv = raw_cv * (1.0 + cv_margin)
    ft_range_hi = math.ceil(min_flow_tph * 1.25 / 5.0) * 5.0

    record_ids = []
    record_ids.append(
        _upsert_record(
            session,
            record_id="CALC-FCV101-CV",
            domain=RecordDomain.INSTRUMENTATION,
            name="FCV-101 preliminary liquid Cv sizing",
            value={
                "minimum_flow_tph": round(min_flow_tph, 3),
                "flow_m3h": round(q_m3h, 3),
                "specific_gravity": round(sg, 4),
                "sizing_dp_bar": cv_dp,
                "raw_cv": round(raw_cv, 3),
                "design_cv": round(design_cv, 3),
                "cv_margin_pct": round(cv_margin * 100.0, 3),
            },
            unit=None,
            status="instrument_checked_demo",
            source_id="CALC-FCV101-001",
            method="demo liquid Kv/Cv equation using published Design Basis",
            object_ids=["VLV-FCV101", "EQ-P101"],
        )
    )
    record_ids.append(
        _upsert_record(
            session,
            record_id="INST-FT101-RANGE",
            domain=RecordDomain.INSTRUMENTATION,
            name="FT-101 preliminary calibrated range",
            value={"LRV": 0.0, "URV": ft_range_hi, "unit": "t/h"},
            unit=None,
            status="instrument_checked_demo",
            source_id="INST-FT101-RANGE",
            method="1.25 × minimum-flow design rate rounded upward",
            object_ids=["INS-FT101", "EQ-P101"],
        )
    )
    record_ids.append(
        _upsert_record(
            session,
            record_id="DCS-FIC101-LOOP",
            domain=RecordDomain.INSTRUMENTATION,
            name="DCS minimum-flow control loop",
            value={
                "measurement": "FT-101",
                "controller": "FIC-101",
                "final_element": "FCV-101",
                "signal_standard": signal_standard,
                "valve_fail_position": fail_position,
                "normal_opening_target_pct": normal_opening,
                "maximum_opening_limit_pct": max_opening,
                "control_action": "TBD during detailed control narrative",
            },
            unit=None,
            status="dcs_basis_published_demo",
            source_id="DCS-FIC101-LOOP",
            method="approved P&ID module + Design Basis instrumentation criteria",
            object_ids=["INS-FT101", "INS-FIC101", "VLV-FCV101", "EQ-P101"],
        )
    )
    record_ids.append(
        _upsert_record(
            session,
            record_id="DCS-LIC101-LOOP",
            domain=RecordDomain.INSTRUMENTATION,
            name="DCS vessel level control loop",
            value={
                "measurement": "LT-101",
                "controller": "LIC-101",
                "final_element": "LCV-101",
                "signal_standard": signal_standard,
                "measurement_range": "0-100 % level",
                "alarm_trip_settings": "TBD by safeguarding / operating philosophy",
            },
            unit=None,
            status="dcs_basis_published_demo",
            source_id="DCS-LIC101-LOOP",
            method="approved vessel level-control module + DCS standard",
            object_ids=["INS-LT101", "INS-LIC101", "VLV-LCV101", "EQ-V101"],
        )
    )

    result = _set_stage(
        session,
        stage=PublishStage.INSTRUMENTATION,
        summary={
            "records": record_ids,
            "FCV-101_design_cv": round(design_cv, 3),
            "FT-101_range": f"0-{ft_range_hi:g} t/h",
            "DCS_loops": ["FIC-101", "LIC-101"],
        },
    )
    result.records_written = record_ids
    session.commit()
    return result


def publish_mechanical(session: Session) -> PublicationResult:
    _require_dependencies(session, PublishStage.MECHANICAL)
    n = _process_numbers(session)
    max_case = publish_demo_simulation("CASE-MAX")
    max_temp = max(stream.temperature for stream in max_case.streams)
    design_temp_margin = float(_criterion(session, "DBC-VESSEL-DT-MARGIN"))
    vessel_moc = str(_criterion(session, "DBC-VESSEL-MOC"))
    corrosion_allowance = float(_criterion(session, "DBC-VESSEL-CA"))
    vessel_code = str(_criterion(session, "DBC-VESSEL-CODE"))
    psv_set = float(_criterion(session, "DBC-PSV-SET-PRESSURE"))

    record_ids = []
    record_ids.append(
        _upsert_record(
            session,
            record_id="MECH-V101",
            domain=RecordDomain.MECHANICAL,
            name="V-101 preliminary mechanical datasheet basis",
            value={
                "design_pressure_barg": psv_set,
                "design_temperature_degC": round(max_temp + design_temp_margin, 3),
                "material_of_construction": vessel_moc,
                "corrosion_allowance_mm": corrosion_allowance,
                "design_code": vessel_code,
                "process_holdup_volume_m3": round(n["holdup_volume_m3"], 3),
                "final_thickness_and_nozzles": "TBD by mechanical design service",
            },
            unit=None,
            status="mechanical_basis_published_demo",
            source_id="MECH-DATASHEET-V101",
            method="published process duty + Design Basis mechanical criteria",
            object_ids=["EQ-V101"],
        )
    )
    record_ids.append(
        _upsert_record(
            session,
            record_id="MECH-P101",
            domain=RecordDomain.MECHANICAL,
            name="P-101 preliminary package datasheet basis",
            value={
                "rated_flow_tph": round(n["pump_rated_flow_tph"], 3),
                "rated_head_m": round(n["pump_rated_head_m"], 3),
                "preliminary_shaft_power_kw": round(n["pump_shaft_kw"], 3),
                "preliminary_motor_kw": round(n["motor_preliminary_kw"], 3),
                "driver": "electric motor",
                "vendor_curve": "TBD during vendor stage",
            },
            unit=None,
            status="mechanical_basis_published_demo",
            source_id="MECH-DATASHEET-P101",
            method="published process duty to mechanical package basis",
            object_ids=["EQ-P101"],
        )
    )

    result = _set_stage(
        session,
        stage=PublishStage.MECHANICAL,
        summary={
            "records": record_ids,
            "V-101_design_temperature_degC": round(max_temp + design_temp_margin, 3),
            "P-101_preliminary_motor_kw": round(n["motor_preliminary_kw"], 3),
        },
    )
    result.records_written = record_ids
    session.commit()
    return result


def _instrumentation_cv(session: Session) -> float:
    row = session.get(EngineeringRecordRow, "CALC-FCV101-CV")
    if row is None or not isinstance(row.value_json, dict):
        raise PublicationBlocked("Published FCV-101 Cv sizing is required for costing.")
    return float(row.value_json["design_cv"])


def publish_costing(session: Session) -> PublicationResult:
    _require_dependencies(session, PublishStage.COSTING)
    n = _process_numbers(session)
    design_cv = _instrumentation_cv(session)
    currency = str(_criterion(session, "DBC-COST-CURRENCY"))

    # Deliberately transparent demo parametric model; not a commercial estimate.
    vessel_cost = 75000.0 + n["holdup_volume_m3"] * 4200.0
    pump_cost = 18000.0 + n["motor_preliminary_kw"] * 950.0
    valve_cost = 5000.0 + design_cv * 180.0
    instrumentation_package = 22000.0
    total = vessel_cost + pump_cost + valve_cost + instrumentation_package

    record_ids = []
    for record_id, name, value, objects in [
        ("COST-V101", "V-101 demo parametric class estimate", vessel_cost, ["EQ-V101"]),
        ("COST-P101", "P-101 demo parametric class estimate", pump_cost, ["EQ-P101"]),
        ("COST-FCV101", "FCV-101 demo parametric class estimate", valve_cost, ["VLV-FCV101"]),
    ]:
        record_ids.append(
            _upsert_record(
                session,
                record_id=record_id,
                domain=RecordDomain.COST,
                name=name,
                value=round(value, 2),
                unit=currency,
                status="class_estimate_demo",
                source_id="COST-MODEL-DEMO-V1",
                method="transparent demo parametric estimate; replace with qualified company cost model",
                object_ids=objects,
                metadata={"estimate_class": "demo", "commercial_use": False},
            )
        )

    record_ids.append(
        _upsert_record(
            session,
            record_id="COST-PACKAGE-TOTAL",
            domain=RecordDomain.COST,
            name="Demo section total installed-equipment basis",
            value={
                "currency": currency,
                "vessel": round(vessel_cost, 2),
                "pump": round(pump_cost, 2),
                "control_valve": round(valve_cost, 2),
                "instrumentation_package": round(instrumentation_package, 2),
                "total": round(total, 2),
            },
            unit=None,
            status="class_estimate_demo",
            source_id="COST-MODEL-DEMO-V1",
            method="sum of demo parametric discipline estimates",
            object_ids=["EQ-V101", "EQ-P101", "VLV-FCV101"],
            metadata={"estimate_class": "demo", "commercial_use": False},
        )
    )

    result = _set_stage(
        session,
        stage=PublishStage.COSTING,
        summary={
            "records": record_ids,
            "currency": currency,
            "demo_total": round(total, 2),
            "note": "Replace demo coefficients with approved licensor/company cost model.",
        },
    )
    result.records_written = record_ids
    session.commit()
    return result


_PUBLISHERS = {
    PublishStage.DESIGN_BASIS: publish_design_basis,
    PublishStage.SIMULATION: publish_simulation,
    PublishStage.CONFIGURATION: publish_configuration,
    PublishStage.PROCESS: publish_process,
    PublishStage.INSTRUMENTATION: publish_instrumentation,
    PublishStage.MECHANICAL: publish_mechanical,
    PublishStage.COSTING: publish_costing,
}


def publish_stage(session: Session, stage: PublishStage) -> PublicationResult:
    return _PUBLISHERS[stage](session)


def publish_all(session: Session) -> list[PublicationResult]:
    results = []
    for stage in STAGE_ORDER:
        results.append(publish_stage(session, stage))
    return results
