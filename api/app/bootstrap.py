from __future__ import annotations

import os

from . import models
from .db import SessionLocal
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

