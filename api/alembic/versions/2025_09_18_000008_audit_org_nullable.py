"""make audit_events.org_id nullable

Revision ID: 000008
Revises: 000007
Create Date: 2025-09-18 02:30:00

"""

import sqlalchemy as sa
from alembic import op

revision = "000008"
down_revision = "000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("audit_events") as batch_op:
        batch_op.alter_column("org_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("audit_events") as batch_op:
        batch_op.alter_column("org_id", existing_type=sa.Integer(), nullable=False)
