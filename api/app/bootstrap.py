from __future__ import annotations

import os

from . import models
from .db import SessionLocal
from sqlalchemy import text
from .security import hash_password


def create_default_superadmin() -> None:
    email = os.getenv("DEFAULT_SUPERADMIN_EMAIL")
    password = os.getenv("DEFAULT_SUPERADMIN_PASSWORD")
    org_name = os.getenv("DEFAULT_SUPERADMIN_ORG", "default")
    if not email or not password:
        return  # not configured

    with SessionLocal() as db:
        # Ensure org exists
        org = db.query(models.Org).filter(models.Org.name == org_name).first()
        if not org:
            org = models.Org(name=org_name)
            db.add(org)
            db.flush()

        # Ensure user exists
        user = db.query(models.User).filter(models.User.email == email).first()
        if user:
            # Ensure it has superadmin role
            roles = set(user.roles or [])
            roles.update(["superadmin", "org_admin", "designer"])
            user.roles = list(roles)
            if user.org_id is None:
                user.org_id = org.id
            db.add(user)
            db.commit()
            return

        user = models.User(
            email=email,
            hashed_password=hash_password(password),
            org_id=org.id,
            roles=["superadmin", "org_admin", "designer"],
        )
        db.add(user)
        db.commit()


def repair_sequences() -> None:
    """
    Ensure PostgreSQL sequences are in sync with current MAX(id) for tables.
    Useful after earlier seeds that inserted explicit ids.
    No-op on databases that don't support pg_get_serial_sequence.
    """
    tables = [
        "orgs",
        "users",
        "projects",
        "project_memberships",
        "design_artifacts",
        "anthropometric_datasets",
        "ability_profiles",
        "rule_packs",
        "simulation_scenarios",
        "evaluation_runs",
        "adaptive_components",
        "reports",
    ]
    try:
        with SessionLocal() as db:
            for t in tables:
                stmt = text(
                    f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {t}), 0) + 1, false)"
                )
                try:
                    db.execute(stmt)
                except Exception:
                    # ignore if table or sequence not present
                    continue
            db.commit()
    except Exception:
        # Do not block startup if this fails
        pass
