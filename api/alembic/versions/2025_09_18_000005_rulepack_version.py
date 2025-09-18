"""add version to rule_packs

Revision ID: 000005
Revises: 000004
Create Date: 2025-09-18 01:20:00

"""
from alembic import op
import sqlalchemy as sa


revision = "000005"
down_revision = "000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rule_packs", sa.Column("version", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("rule_packs", "version")

