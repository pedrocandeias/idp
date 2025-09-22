"""project memberships

Revision ID: 000009
Revises: 000008
Create Date: 2025-09-22 00:09:00

"""

import sqlalchemy as sa
from alembic import op

revision = "000009"
down_revision = "000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_project_user", "project_memberships", ["project_id", "user_id"])


def downgrade() -> None:
    op.drop_constraint("uq_project_user", "project_memberships", type_="unique")
    op.drop_table("project_memberships")

