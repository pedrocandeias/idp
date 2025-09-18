"""artifact storage fields

Revision ID: 000003
Revises: 000002
Create Date: 2025-09-18 00:40:00

"""
from alembic import op
import sqlalchemy as sa


revision = "000003"
down_revision = "000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("design_artifacts", sa.Column("object_key", sa.String(length=1024), nullable=True))
    op.add_column("design_artifacts", sa.Column("params_key", sa.String(length=1024), nullable=True))
    op.add_column("design_artifacts", sa.Column("object_mime", sa.String(length=255), nullable=True))
    op.add_column("design_artifacts", sa.Column("size_bytes", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("design_artifacts", "size_bytes")
    op.drop_column("design_artifacts", "object_mime")
    op.drop_column("design_artifacts", "params_key")
    op.drop_column("design_artifacts", "object_key")

