from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProjectRow(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    technology: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="working")


class DesignBasisRevisionRow(Base):
    __tablename__ = "design_basis_revisions"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    revision: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(40))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DesignBasisCriterionRow(Base):
    __tablename__ = "design_basis_criteria"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    design_basis_revision_id: Mapped[str] = mapped_column(ForeignKey("design_basis_revisions.id"), index=True)
    name: Mapped[str] = mapped_column(String(250))
    category: Mapped[str] = mapped_column(String(80), index=True)
    value_json: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(40))
    applicability_json: Mapped[dict] = mapped_column(JSON, default=dict)
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict)


class CriterionObjectLinkRow(Base):
    __tablename__ = "criterion_object_links"
    __table_args__ = (UniqueConstraint("criterion_id", "object_id", name="uq_criterion_object"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criterion_id: Mapped[str] = mapped_column(ForeignKey("design_basis_criteria.id"), index=True)
    object_id: Mapped[str] = mapped_column(String(100), index=True)


class DesignCaseRow(Base):
    __tablename__ = "design_cases"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    design_basis_revision_id: Mapped[str] = mapped_column(ForeignKey("design_basis_revisions.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    case_type: Mapped[str] = mapped_column(String(60), index=True)
    status: Mapped[str] = mapped_column(String(40))


class SimulationCaseRow(Base):
    __tablename__ = "simulation_cases"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    design_case_id: Mapped[str] = mapped_column(ForeignKey("design_cases.id"), index=True)
    simulator: Mapped[str] = mapped_column(String(100))
    simulator_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(40))
    run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class EquipmentRow(Base):
    """Canonical PFD equipment object; one row per plant object, not per case."""
    __tablename__ = "equipment"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    simulation_object_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tag: Mapped[str] = mapped_column(String(80), index=True)
    equipment_type: Mapped[str] = mapped_column(String(100))
    service: Mapped[str | None] = mapped_column(String(250), nullable=True)


class StreamRow(Base):
    """Canonical PFD stream topology; thermodynamic values are stored by case."""
    __tablename__ = "streams"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    simulation_stream_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    stream_number: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    source_equipment_id: Mapped[str | None] = mapped_column(ForeignKey("equipment.id"), nullable=True, index=True)
    destination_equipment_id: Mapped[str | None] = mapped_column(ForeignKey("equipment.id"), nullable=True, index=True)


class StreamCaseResultRow(Base):
    __tablename__ = "stream_case_results"
    __table_args__ = (UniqueConstraint("stream_id", "simulation_case_id", name="uq_stream_case"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[str] = mapped_column(ForeignKey("streams.id"), index=True)
    simulation_case_id: Mapped[str] = mapped_column(ForeignKey("simulation_cases.id"), index=True)
    phase: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mass_flow: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    density: Mapped[float | None] = mapped_column(Float, nullable=True)
    viscosity: Mapped[float | None] = mapped_column(Float, nullable=True)
    enthalpy: Mapped[float | None] = mapped_column(Float, nullable=True)
    units_json: Mapped[dict] = mapped_column(JSON, default=dict)


class StreamComponentRow(Base):
    __tablename__ = "stream_components"
    __table_args__ = (UniqueConstraint("stream_case_result_id", "component", name="uq_stream_component_case"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_case_result_id: Mapped[int] = mapped_column(ForeignKey("stream_case_results.id"), index=True)
    component: Mapped[str] = mapped_column(String(100))
    mole_fraction: Mapped[float | None] = mapped_column(Float, nullable=True)
    mass_fraction: Mapped[float | None] = mapped_column(Float, nullable=True)



class ProcessConfigurationRow(Base):
    __tablename__ = "process_configurations"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(String(250))
    version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), index=True)
    definition_json: Mapped[dict] = mapped_column(JSON)
    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)



class PublicationStageRow(Base):
    __tablename__ = "publication_stages"
    __table_args__ = (
        UniqueConstraint("project_id", "stage", name="uq_project_publication_stage"),
    )
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    stage: Mapped[str] = mapped_column(String(80), index=True)
    revision: Mapped[str] = mapped_column(String(40), default="A")
    status: Mapped[str] = mapped_column(String(40), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict)


class EngineeringRecordRow(Base):
    __tablename__ = "engineering_records"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    domain: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(250))
    value_json: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(40))
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class RecordObjectLinkRow(Base):
    __tablename__ = "record_object_links"
    __table_args__ = (
        UniqueConstraint(
            "engineering_record_id",
            "object_id",
            "relationship",
            name="uq_record_object_relationship",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    engineering_record_id: Mapped[str] = mapped_column(ForeignKey("engineering_records.id"), index=True)
    object_id: Mapped[str] = mapped_column(String(100), index=True)
    relationship: Mapped[str] = mapped_column(String(80), default="applies_to")


def engine_from_url(database_url: str | None = None):
    url = database_url or os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    return create_engine(url)


def create_schema(database_url: str | None = None):
    engine = engine_from_url(database_url)
    Base.metadata.create_all(engine)
    return engine
