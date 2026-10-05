"""Digital BDEP core database

Revision ID: 0001_core
Revises:
Create Date: 2026-10-04
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_core"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("technology", sa.String(200), nullable=True),
        sa.Column("status", sa.String(40), nullable=False),
    )
    op.create_table(
        "design_basis_revisions",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("project_id", sa.String(80), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("revision", sa.String(20), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_design_basis_revisions_project_id", "design_basis_revisions", ["project_id"])

    op.create_table(
        "design_basis_criteria",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("design_basis_revision_id", sa.String(80), sa.ForeignKey("design_basis_revisions.id"), nullable=False),
        sa.Column("name", sa.String(250), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("unit", sa.String(40), nullable=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("applicability_json", sa.JSON(), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_design_basis_criteria_design_basis_revision_id", "design_basis_criteria", ["design_basis_revision_id"])
    op.create_index("ix_design_basis_criteria_category", "design_basis_criteria", ["category"])

    op.create_table(
        "criterion_object_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("criterion_id", sa.String(100), sa.ForeignKey("design_basis_criteria.id"), nullable=False),
        sa.Column("object_id", sa.String(100), nullable=False),
        sa.UniqueConstraint("criterion_id", "object_id", name="uq_criterion_object"),
    )
    op.create_index("ix_criterion_object_links_criterion_id", "criterion_object_links", ["criterion_id"])
    op.create_index("ix_criterion_object_links_object_id", "criterion_object_links", ["object_id"])

    op.create_table(
        "design_cases",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("design_basis_revision_id", sa.String(80), sa.ForeignKey("design_basis_revisions.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("case_type", sa.String(60), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
    )
    op.create_index("ix_design_cases_design_basis_revision_id", "design_cases", ["design_basis_revision_id"])
    op.create_index("ix_design_cases_case_type", "design_cases", ["case_type"])

    op.create_table(
        "simulation_cases",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("project_id", sa.String(80), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("design_case_id", sa.String(80), sa.ForeignKey("design_cases.id"), nullable=False),
        sa.Column("simulator", sa.String(100), nullable=False),
        sa.Column("simulator_version", sa.String(100), nullable=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("run_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_simulation_cases_project_id", "simulation_cases", ["project_id"])
    op.create_index("ix_simulation_cases_design_case_id", "simulation_cases", ["design_case_id"])

    op.create_table(
        "equipment",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("project_id", sa.String(80), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("simulation_object_id", sa.String(120), nullable=True),
        sa.Column("tag", sa.String(80), nullable=False),
        sa.Column("equipment_type", sa.String(100), nullable=False),
        sa.Column("service", sa.String(250), nullable=True),
    )
    op.create_index("ix_equipment_project_id", "equipment", ["project_id"])
    op.create_index("ix_equipment_tag", "equipment", ["tag"])

    op.create_table(
        "streams",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("project_id", sa.String(80), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("simulation_stream_id", sa.String(120), nullable=True),
        sa.Column("source_equipment_id", sa.String(100), sa.ForeignKey("equipment.id"), nullable=True),
        sa.Column("destination_equipment_id", sa.String(100), sa.ForeignKey("equipment.id"), nullable=True),
    )
    op.create_index("ix_streams_project_id", "streams", ["project_id"])
    op.create_index("ix_streams_source_equipment_id", "streams", ["source_equipment_id"])
    op.create_index("ix_streams_destination_equipment_id", "streams", ["destination_equipment_id"])

    op.create_table(
        "stream_case_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("stream_id", sa.String(100), sa.ForeignKey("streams.id"), nullable=False),
        sa.Column("simulation_case_id", sa.String(80), sa.ForeignKey("simulation_cases.id"), nullable=False),
        sa.Column("phase", sa.String(40), nullable=True),
        sa.Column("mass_flow", sa.Float(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("pressure", sa.Float(), nullable=True),
        sa.Column("density", sa.Float(), nullable=True),
        sa.Column("viscosity", sa.Float(), nullable=True),
        sa.Column("enthalpy", sa.Float(), nullable=True),
        sa.Column("units_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("stream_id", "simulation_case_id", name="uq_stream_case"),
    )
    op.create_index("ix_stream_case_results_stream_id", "stream_case_results", ["stream_id"])
    op.create_index("ix_stream_case_results_simulation_case_id", "stream_case_results", ["simulation_case_id"])

    op.create_table(
        "stream_components",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("stream_case_result_id", sa.Integer(), sa.ForeignKey("stream_case_results.id"), nullable=False),
        sa.Column("component", sa.String(100), nullable=False),
        sa.Column("mole_fraction", sa.Float(), nullable=True),
        sa.Column("mass_fraction", sa.Float(), nullable=True),
        sa.UniqueConstraint("stream_case_result_id", "component", name="uq_stream_component_case"),
    )
    op.create_index("ix_stream_components_stream_case_result_id", "stream_components", ["stream_case_result_id"])

    op.create_table(
        "engineering_records",
        sa.Column("id", sa.String(120), primary_key=True),
        sa.Column("project_id", sa.String(80), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("domain", sa.String(80), nullable=False),
        sa.Column("name", sa.String(250), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("unit", sa.String(40), nullable=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_engineering_records_project_id", "engineering_records", ["project_id"])
    op.create_index("ix_engineering_records_domain", "engineering_records", ["domain"])

    op.create_table(
        "record_object_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("engineering_record_id", sa.String(120), sa.ForeignKey("engineering_records.id"), nullable=False),
        sa.Column("object_id", sa.String(100), nullable=False),
        sa.Column("relationship", sa.String(80), nullable=False),
        sa.UniqueConstraint(
            "engineering_record_id",
            "object_id",
            "relationship",
            name="uq_record_object_relationship",
        ),
    )
    op.create_index("ix_record_object_links_engineering_record_id", "record_object_links", ["engineering_record_id"])
    op.create_index("ix_record_object_links_object_id", "record_object_links", ["object_id"])


def downgrade() -> None:
    op.drop_table("record_object_links")
    op.drop_table("engineering_records")
    op.drop_table("stream_components")
    op.drop_table("stream_case_results")
    op.drop_table("streams")
    op.drop_table("equipment")
    op.drop_table("simulation_cases")
    op.drop_table("design_cases")
    op.drop_table("criterion_object_links")
    op.drop_table("design_basis_criteria")
    op.drop_table("design_basis_revisions")
    op.drop_table("projects")
