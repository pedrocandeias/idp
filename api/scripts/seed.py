#!/usr/bin/env python
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal, engine
from app import models


def ensure_default_org(db: Session) -> models.Org:
    org = db.query(models.Org).filter(models.Org.name == "default").first()
    if not org:
        org = models.Org(name="default")
        db.add(org)
        db.commit()
        db.refresh(org)
    return org


def seed():
    base = Path(__file__).resolve().parent.parent / "seeds"
    anthro_path = base / "anthropometrics_demo.json"
    abil_path = base / "abilities_demo.json"

    with SessionLocal() as db:
        org = ensure_default_org(db)

        # Anthropometrics
        if anthro_path.exists():
            data = json.loads(anthro_path.read_text())
            existing = db.query(models.AnthropometricDataset).filter(
                models.AnthropometricDataset.name == data.get("name")
            ).first()
            if not existing:
                item = models.AnthropometricDataset(
                    org_id=org.id,
                    name=data.get("name"),
                    source=data.get("source"),
                    schema=data.get("schema"),
                    distributions=data.get("distributions"),
                )
                db.add(item)
                db.commit()

        # Abilities
        if abil_path.exists():
            data = json.loads(abil_path.read_text())
            existing = db.query(models.AbilityProfile).filter(
                models.AbilityProfile.name == data.get("name")
            ).first()
            if not existing:
                item = models.AbilityProfile(
                    org_id=org.id,
                    name=data.get("name"),
                    data=data.get("data"),
                )
                db.add(item)
                db.commit()


if __name__ == "__main__":
    seed()
