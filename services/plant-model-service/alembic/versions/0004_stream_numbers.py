"""Add engineering stream numbers

Revision ID: 0004_stream_numbers
Revises: 0003_publication_stages
Create Date: 2026-10-04
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_stream_numbers"
down_revision = "0003_publication_stages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("streams", sa.Column("stream_number", sa.String(20), nullable=True))
    op.create_index("ix_streams_stream_number", "streams", ["stream_number"])


def downgrade() -> None:
    op.drop_index("ix_streams_stream_number", table_name="streams")
    op.drop_column("streams", "stream_number")
