"""add anthropometric distributions json

Revision ID: 000004
Revises: 000003
Create Date: 2025-09-18 01:00:00

"""

import sqlalchemy as sa
from alembic import op

revision = "000004"
down_revision = "000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "anthropometric_datasets",
        sa.Column("distributions", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("anthropometric_datasets", "distributions")
