"""add storage fields to reports

Revision ID: 000007
Revises: 000006
Create Date: 2025-09-18 02:00:00

"""

import sqlalchemy as sa
from alembic import op

revision = "000007"
down_revision = "000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reports", sa.Column("html_key", sa.String(length=1024), nullable=True)
    )
    op.add_column(
        "reports", sa.Column("pdf_key", sa.String(length=1024), nullable=True)
    )
    op.add_column(
        "reports", sa.Column("checksum_sha256", sa.String(length=64), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("reports", "checksum_sha256")
    op.drop_column("reports", "pdf_key")
    op.drop_column("reports", "html_key")
