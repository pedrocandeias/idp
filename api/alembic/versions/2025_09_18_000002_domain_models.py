"""domain models

Revision ID: 000002
Revises: 000001
Create Date: 2025-09-18 00:20:00

"""

import sqlalchemy as sa
from alembic import op

revision = "000002"
down_revision = "000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users.roles
    op.add_column(
        "users",
        sa.Column(
            "roles",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[\"designer\"]'::jsonb"),
        ),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "design_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=True),
        sa.Column("uri", sa.String(length=1024), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "anthropometric_datasets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("schema", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "ability_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "rule_packs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "simulation_scenarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scenario_id",
            sa.Integer(),
            sa.ForeignKey("simulation_scenarios.id"),
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="pending"
        ),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "adaptive_components",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("spec", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("reports")
    op.drop_table("adaptive_components")
    op.drop_table("evaluation_runs")
    op.drop_table("simulation_scenarios")
    op.drop_table("rule_packs")
    op.drop_table("ability_profiles")
    op.drop_table("anthropometric_datasets")
    op.drop_table("design_artifacts")
    op.drop_table("projects")
    op.drop_column("users", "roles")
