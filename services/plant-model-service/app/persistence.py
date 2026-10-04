from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from .configurations import demo_integrated_configuration_model
from .db_schema import (
    CriterionObjectLinkRow,
    DesignBasisCriterionRow,
    DesignBasisRevisionRow,
    DesignCaseRow,
    EngineeringRecordRow,
    EquipmentRow,
    ProjectRow,
    RecordObjectLinkRow,
    SimulationCaseRow,
    StreamCaseResultRow,
    StreamComponentRow,
    StreamRow,
)
from .simulation import publish_demo_simulation
from .thread_models import (
    CriterionCategory,
    CriterionStatus,
    DesignBasisCriterion,
    EngineeringRecord,
    ObjectDossier,
    Provenance,
    RecordDomain,
)
from .thread_service import (
    DESIGN_BASIS_CRITERIA,
    DESIGN_CASES,
    ENGINEERING_RECORDS,
    _object_type,
)


PROJECT_ID = "BDEP-DEMO-004"
DESIGN_BASIS_REVISION_ID = "DB-001-A"


def _clear_demo(session: Session) -> None:
    for table in [
        RecordObjectLinkRow,
        EngineeringRecordRow,
        StreamComponentRow,
        StreamCaseResultRow,
        StreamRow,
        EquipmentRow,
        SimulationCaseRow,
        DesignCaseRow,
        CriterionObjectLinkRow,
        DesignBasisCriterionRow,
        DesignBasisRevisionRow,
        ProjectRow,
    ]:
        session.execute(delete(table))


def seed_demo_database(engine) -> dict[str, int]:
    """Reset and seed the demo Digital BDEP database deterministically."""
    model = demo_integrated_configuration_model()
    publications = [publish_demo_simulation(case.id) for case in DESIGN_CASES]
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal.begin() as session:
        _clear_demo(session)

        session.add(
            ProjectRow(
                id=PROJECT_ID,
                name="Digital BDEP Demo Project",
                technology="Demo Process Technology",
                status="working",
            )
        )
        session.add(
            DesignBasisRevisionRow(
                id=DESIGN_BASIS_REVISION_ID,
                project_id=PROJECT_ID,
                revision="A",
                status="approved",
            )
        )

        object_ids = {obj.id for obj in model.objects}
        criterion_links = 0
        for criterion in DESIGN_BASIS_CRITERIA:
            session.add(
                DesignBasisCriterionRow(
                    id=criterion.id,
                    design_basis_revision_id=DESIGN_BASIS_REVISION_ID,
                    name=criterion.name,
                    category=criterion.category.value,
                    value_json=criterion.value,
                    unit=criterion.unit,
                    status=criterion.status.value,
                    applicability_json={
                        "categories": criterion.applies_to_categories,
                        "types": criterion.applies_to_types,
                        "targets": criterion.target_object_ids,
                    },
                    provenance_json=criterion.provenance.model_dump(mode="json"),
                )
            )
            for obj in model.objects:
                if criterion.applies_to(
                    object_id=obj.id,
                    category=obj.category,
                    object_type=_object_type(obj),
                ):
                    session.add(
                        CriterionObjectLinkRow(
                            criterion_id=criterion.id,
                            object_id=obj.id,
                        )
                    )
                    criterion_links += 1

        for case in DESIGN_CASES:
            session.add(
                DesignCaseRow(
                    id=case.id,
                    design_basis_revision_id=DESIGN_BASIS_REVISION_ID,
                    name=case.name,
                    case_type=case.case_type,
                    status=case.status,
                )
            )

        normal_pub = publications[0]
        for equipment in normal_pub.equipment:
            session.add(
                EquipmentRow(
                    id=equipment.id,
                    project_id=PROJECT_ID,
                    simulation_object_id=equipment.simulator_object_id,
                    tag=equipment.tag,
                    equipment_type=equipment.equipment_type,
                    service=equipment.service,
                )
            )

        for stream in normal_pub.streams:
            session.add(
                StreamRow(
                    id=stream.id,
                    project_id=PROJECT_ID,
                    simulation_stream_id=stream.simulator_stream_id,
                    source_equipment_id=stream.source_equipment_id,
                    destination_equipment_id=stream.destination_equipment_id,
                )
            )

        result_count = 0
        component_count = 0
        for publication in publications:
            session.add(
                SimulationCaseRow(
                    id=publication.simulation_case_id,
                    project_id=PROJECT_ID,
                    design_case_id=publication.design_case_id,
                    simulator=publication.simulator,
                    simulator_version="demo-1",
                    status=publication.status,
                )
            )
            session.flush()

            for stream in publication.streams:
                result = StreamCaseResultRow(
                    stream_id=stream.id,
                    simulation_case_id=publication.simulation_case_id,
                    phase=stream.phase,
                    mass_flow=stream.mass_flow,
                    temperature=stream.temperature,
                    pressure=stream.pressure,
                    density=stream.density,
                    viscosity=stream.viscosity,
                    enthalpy=stream.enthalpy,
                    units_json={
                        "mass_flow": stream.mass_flow_unit,
                        "temperature": stream.temperature_unit,
                        "pressure": stream.pressure_unit,
                        "density": stream.density_unit,
                        "viscosity": stream.viscosity_unit,
                        "enthalpy": stream.enthalpy_unit,
                    },
                )
                session.add(result)
                session.flush()
                result_count += 1

                for component, mole_fraction in stream.composition.items():
                    session.add(
                        StreamComponentRow(
                            stream_case_result_id=result.id,
                            component=component,
                            mole_fraction=mole_fraction,
                        )
                    )
                    component_count += 1

        record_links = 0
        for record in ENGINEERING_RECORDS:
            session.add(
                EngineeringRecordRow(
                    id=record.id,
                    project_id=PROJECT_ID,
                    domain=record.domain.value,
                    name=record.name,
                    value_json=record.value,
                    unit=record.unit,
                    status=record.status,
                    provenance_json=record.provenance.model_dump(mode="json"),
                    metadata_json=record.metadata,
                )
            )
            session.add(
                RecordObjectLinkRow(
                    engineering_record_id=record.id,
                    object_id=record.object_id,
                    relationship="applies_to",
                )
            )
            record_links += 1

    return {
        "projects": 1,
        "criteria": len(DESIGN_BASIS_CRITERIA),
        "criterion_links": criterion_links,
        "design_cases": len(DESIGN_CASES),
        "simulation_cases": len(publications),
        "equipment": len(normal_pub.equipment),
        "streams": len(normal_pub.streams),
        "stream_case_results": result_count,
        "stream_components": component_count,
        "engineering_records": len(ENGINEERING_RECORDS),
        "record_links": record_links,
    }


def load_object_dossier(session: Session, object_id: str) -> ObjectDossier:
    model = demo_integrated_configuration_model()
    obj = model.object(object_id)

    criterion_rows = session.scalars(
        select(DesignBasisCriterionRow)
        .join(
            CriterionObjectLinkRow,
            CriterionObjectLinkRow.criterion_id == DesignBasisCriterionRow.id,
        )
        .where(CriterionObjectLinkRow.object_id == object_id)
        .order_by(DesignBasisCriterionRow.category, DesignBasisCriterionRow.id)
    ).all()

    criteria = []
    for row in criterion_rows:
        applicability = row.applicability_json or {}
        criteria.append(
            DesignBasisCriterion(
                id=row.id,
                name=row.name,
                category=CriterionCategory(row.category),
                value=row.value_json,
                unit=row.unit,
                revision="A",
                status=CriterionStatus(row.status),
                applies_to_categories=applicability.get("categories", []),
                applies_to_types=applicability.get("types", []),
                target_object_ids=applicability.get("targets", []),
                provenance=Provenance.model_validate(row.provenance_json),
            )
        )

    record_rows = session.scalars(
        select(EngineeringRecordRow)
        .join(
            RecordObjectLinkRow,
            RecordObjectLinkRow.engineering_record_id == EngineeringRecordRow.id,
        )
        .where(RecordObjectLinkRow.object_id == object_id)
        .order_by(EngineeringRecordRow.domain, EngineeringRecordRow.id)
    ).all()

    grouped: dict[RecordDomain, list[EngineeringRecord]] = {}
    for row in record_rows:
        domain = RecordDomain(row.domain)
        grouped.setdefault(domain, []).append(
            EngineeringRecord(
                id=row.id,
                object_id=object_id,
                domain=domain,
                name=row.name,
                value=row.value_json,
                unit=row.unit,
                status=row.status,
                provenance=Provenance.model_validate(row.provenance_json),
                metadata=row.metadata_json or {},
            )
        )

    return ObjectDossier(
        object_id=obj.id,
        tag=obj.tag,
        category=obj.category,
        object_type=_object_type(obj),
        service=obj.service,
        design_basis=criteria,
        records=grouped,
    )


def database_summary(session: Session) -> dict[str, int]:
    entities = {
        "projects": ProjectRow,
        "design_basis_revisions": DesignBasisRevisionRow,
        "design_basis_criteria": DesignBasisCriterionRow,
        "criterion_object_links": CriterionObjectLinkRow,
        "design_cases": DesignCaseRow,
        "simulation_cases": SimulationCaseRow,
        "equipment": EquipmentRow,
        "streams": StreamRow,
        "stream_case_results": StreamCaseResultRow,
        "stream_components": StreamComponentRow,
        "engineering_records": EngineeringRecordRow,
        "record_object_links": RecordObjectLinkRow,
    }
    return {
        name: len(session.scalars(select(entity)).all())
        for name, entity in entities.items()
    }



def ensure_demo_seeded(engine) -> None:
    """Create tables and seed only when the database is empty; never reset populated data."""
    from sqlalchemy import select
    from .db_schema import Base

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        existing = session.scalar(select(ProjectRow.id).limit(1))
    if existing is None:
        seed_demo_database(engine)



def load_configuration_match_facts(session: Session) -> dict[str, str | float | int | bool]:
    """Return approved Design Basis facts used by deterministic configuration matching."""
    row = session.get(DesignBasisCriterionRow, "DBC-PUMP-MIN-FLOW")
    facts: dict[str, str | float | int | bool] = {}
    if row is not None and row.status == "approved":
        facts["pump_minimum_flow_required"] = row.value_json
    return facts
