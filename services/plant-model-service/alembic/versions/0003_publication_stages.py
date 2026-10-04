"""Add discipline publication stages

Revision ID: 0003_publication_stages
Revises: 0002_process_config
Create Date: 2026-10-04
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_publication_stages"
down_revision = "0002_process_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "publication_stages",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("project_id", sa.String(80), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("stage", sa.String(80), nullable=False),
        sa.Column("revision", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("project_id", "stage", name="uq_project_publication_stage"),
    )
    op.create_index("ix_publication_stages_project_id", "publication_stages", ["project_id"])
    op.create_index("ix_publication_stages_stage", "publication_stages", ["stage"])
    op.create_index("ix_publication_stages_status", "publication_stages", ["status"])


def downgrade() -> None:
    op.drop_table("publication_stages")
