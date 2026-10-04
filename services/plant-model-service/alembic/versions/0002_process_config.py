"""Add approved process configuration library

Revision ID: 0002_process_config
Revises: 0001_core
Create Date: 2026-10-04
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_process_config"
down_revision = "0001_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "process_configurations",
        sa.Column("id", sa.String(120), primary_key=True),
        sa.Column("name", sa.String(250), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("definition_json", sa.JSON(), nullable=False),
        sa.Column("approved_by", sa.String(120), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_process_configurations_status",
        "process_configurations",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("process_configurations")
