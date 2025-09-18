"""add results columns to evaluation_runs and inputs

Revision ID: 000006
Revises: 000005
Create Date: 2025-09-18 01:40:00

"""
from alembic import op
import sqlalchemy as sa


revision = "000006"
down_revision = "000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("evaluation_runs", sa.Column("results_json", sa.JSON(), nullable=True))
    op.add_column("evaluation_runs", sa.Column("inclusivity_index_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("evaluation_runs", "inclusivity_index_json")
    op.drop_column("evaluation_runs", "results_json")

