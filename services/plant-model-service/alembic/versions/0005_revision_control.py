"""Add engineering revision, review, integration and client issue control

Revision ID: 0005_revision_control
Revises: 0004_stream_numbers
Create Date: 2026-10-05
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_revision_control"
down_revision = "0004_stream_numbers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engineering_baselines",
        sa.Column("id", sa.String(120), primary_key=True),
        sa.Column("project_id", sa.String(80), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("revision", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("parent_baseline_id", sa.String(120), nullable=True),
        sa.Column("model_hash", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("project_id", "revision", name="uq_project_engineering_baseline_revision"),
    )
    op.create_index("ix_engineering_baselines_project_id", "engineering_baselines", ["project_id"])
    op.create_index("ix_engineering_baselines_revision", "engineering_baselines", ["revision"])
    op.create_index("ix_engineering_baselines_status", "engineering_baselines", ["status"])
    op.create_index("ix_engineering_baselines_parent_baseline_id", "engineering_baselines", ["parent_baseline_id"])

    op.create_table(
        "engineering_change_packages",
        sa.Column("id", sa.String(120), primary_key=True),
        sa.Column("project_id", sa.String(80), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("title", sa.String(250), nullable=False),
        sa.Column("discipline", sa.String(80), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("base_baseline_id", sa.String(120), sa.ForeignKey("engineering_baselines.id"), nullable=False),
        sa.Column("working_revision", sa.String(40), nullable=False),
        sa.Column("maker_id", sa.String(120), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("content_hash", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
    )
    for name, cols in [
        ("ix_engineering_change_packages_project_id", ["project_id"]),
        ("ix_engineering_change_packages_discipline", ["discipline"]),
        ("ix_engineering_change_packages_status", ["status"]),
        ("ix_engineering_change_packages_base_baseline_id", ["base_baseline_id"]),
        ("ix_engineering_change_packages_maker_id", ["maker_id"]),
    ]:
        op.create_index(name, "engineering_change_packages", cols)

    op.create_table(
        "engineering_change_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("change_package_id", sa.String(120), sa.ForeignKey("engineering_change_packages.id"), nullable=False),
        sa.Column("object_id", sa.String(120), nullable=False),
        sa.Column("property_path", sa.String(250), nullable=False),
        sa.Column("change_type", sa.String(40), nullable=False),
        sa.Column("base_object_revision", sa.Integer(), nullable=False),
        sa.Column("base_value_json", sa.JSON(), nullable=True),
        sa.Column("proposed_value_json", sa.JSON(), nullable=True),
        sa.Column("unit", sa.String(40), nullable=True),
        sa.Column("impact_state", sa.String(50), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_engineering_change_records_change_package_id", "engineering_change_records", ["change_package_id"])
    op.create_index("ix_engineering_change_records_object_id", "engineering_change_records", ["object_id"])
    op.create_index("ix_engineering_change_records_property_path", "engineering_change_records", ["property_path"])
    op.create_index("ix_engineering_change_records_impact_state", "engineering_change_records", ["impact_state"])

    op.create_table(
        "engineering_review_requirements",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("change_package_id", sa.String(120), sa.ForeignKey("engineering_change_packages.id"), nullable=False),
        sa.Column("review_type", sa.String(60), nullable=False),
        sa.Column("discipline", sa.String(80), nullable=False),
        sa.Column("reviewer_role", sa.String(120), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("reviewer_id", sa.String(120), nullable=True),
        sa.Column("reviewed_content_hash", sa.String(128), nullable=True),
        sa.Column("comments", sa.String(1000), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_engineering_review_requirements_change_package_id", "engineering_review_requirements", ["change_package_id"])
    op.create_index("ix_engineering_review_requirements_review_type", "engineering_review_requirements", ["review_type"])
    op.create_index("ix_engineering_review_requirements_discipline", "engineering_review_requirements", ["discipline"])
    op.create_index("ix_engineering_review_requirements_status", "engineering_review_requirements", ["status"])

    op.create_table(
        "engineering_integration_queue",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("change_package_id", sa.String(120), sa.ForeignKey("engineering_change_packages.id"), nullable=False),
        sa.Column("queue_position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("validation_json", sa.JSON(), nullable=False),
        sa.Column("queued_at", sa.DateTime(), nullable=True),
        sa.Column("integrated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("change_package_id", name="uq_integration_change_package"),
        sa.UniqueConstraint("queue_position", name="uq_integration_queue_position"),
    )
    op.create_index("ix_engineering_integration_queue_change_package_id", "engineering_integration_queue", ["change_package_id"])
    op.create_index("ix_engineering_integration_queue_queue_position", "engineering_integration_queue", ["queue_position"])
    op.create_index("ix_engineering_integration_queue_status", "engineering_integration_queue", ["status"])

    op.create_table(
        "release_candidates",
        sa.Column("id", sa.String(120), primary_key=True),
        sa.Column("project_id", sa.String(80), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("baseline_id", sa.String(120), sa.ForeignKey("engineering_baselines.id"), nullable=False),
        sa.Column("revision", sa.String(40), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("project_id", "revision", name="uq_project_release_candidate_revision"),
    )
    op.create_index("ix_release_candidates_project_id", "release_candidates", ["project_id"])
    op.create_index("ix_release_candidates_baseline_id", "release_candidates", ["baseline_id"])
    op.create_index("ix_release_candidates_revision", "release_candidates", ["revision"])
    op.create_index("ix_release_candidates_status", "release_candidates", ["status"])

    op.create_table(
        "client_issues",
        sa.Column("id", sa.String(120), primary_key=True),
        sa.Column("project_id", sa.String(80), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("release_candidate_id", sa.String(120), sa.ForeignKey("release_candidates.id"), nullable=False),
        sa.Column("baseline_id", sa.String(120), sa.ForeignKey("engineering_baselines.id"), nullable=False),
        sa.Column("issue_revision", sa.String(40), nullable=False),
        sa.Column("purpose", sa.String(120), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("supersedes_issue_id", sa.String(120), nullable=True),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=True),
        sa.Column("client_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("project_id", "issue_revision", name="uq_project_client_issue_revision"),
    )
    for name, cols in [
        ("ix_client_issues_project_id", ["project_id"]),
        ("ix_client_issues_release_candidate_id", ["release_candidate_id"]),
        ("ix_client_issues_baseline_id", ["baseline_id"]),
        ("ix_client_issues_issue_revision", ["issue_revision"]),
        ("ix_client_issues_status", ["status"]),
        ("ix_client_issues_supersedes_issue_id", ["supersedes_issue_id"]),
        ("ix_client_issues_client_visible", ["client_visible"]),
    ]:
        op.create_index(name, "client_issues", cols)


def downgrade() -> None:
    for table in [
        "client_issues",
        "release_candidates",
        "engineering_integration_queue",
        "engineering_review_requirements",
        "engineering_change_records",
        "engineering_change_packages",
        "engineering_baselines",
    ]:
        op.drop_table(table)
