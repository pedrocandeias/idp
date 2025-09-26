from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .config import settings
from . import models
from .db import SessionLocal


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _slugify(s: str) -> str:
    return ("" if not s else "".join([c.lower() if c.isalnum() else "-" for c in s])).strip("-") or "item"


def _delete_by_id(dirpath: Path, item_id: int) -> None:
    if not dirpath.exists():
        return
    for p in dirpath.glob(f"*_{item_id}_*.json"):
        try:
            p.unlink(missing_ok=True)
        except Exception:
            continue


def save_rulepack_json(rp: models.RulePack) -> None:
    base = Path(settings.data_dir) / "rulepacks"
    _ensure_dir(base)
    # remove previous files for this id
    _delete_by_id(base, rp.id)
    payload = {
        "id": rp.id,
        "org_id": rp.org_id,
        "name": rp.name,
        "version": getattr(rp, "version", None),
        "rules": rp.rules,
    }
    fname = f"{rp.org_id}_{rp.id}_{_slugify(rp.name)}.json"
    (base / fname).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def delete_rulepack_json(rulepack_id: int) -> None:
    base = Path(settings.data_dir) / "rulepacks"
    _delete_by_id(base, rulepack_id)


def save_anthro_json(ds: models.AnthropometricDataset) -> None:
    base = Path(settings.data_dir) / "anthropometrics"
    _ensure_dir(base)
    _delete_by_id(base, ds.id)
    payload = {
        "id": ds.id,
        "org_id": ds.org_id,
        "name": ds.name,
        "source": ds.source,
        "schema": ds.schema,
        "distributions": ds.distributions,
    }
    fname = f"{ds.org_id}_{ds.id}_{_slugify(ds.name)}.json"
    (base / fname).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def delete_anthro_json(dataset_id: int) -> None:
    base = Path(settings.data_dir) / "anthropometrics"
    _delete_by_id(base, dataset_id)


def save_ability_json(ab: models.AbilityProfile) -> None:
    base = Path(settings.data_dir) / "abilities"
    _ensure_dir(base)
    _delete_by_id(base, ab.id)
    payload = {
        "id": ab.id,
        "org_id": ab.org_id,
        "name": ab.name,
        "data": ab.data,
    }
    fname = f"{ab.org_id}_{ab.id}_{_slugify(ab.name)}.json"
    (base / fname).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def delete_ability_json(ability_id: int) -> None:
    base = Path(settings.data_dir) / "abilities"
    _delete_by_id(base, ability_id)


def load_all_from_json() -> None:
    base = Path(settings.data_dir)
    if not base.exists():
        return
    with SessionLocal() as db:
        # Rulepacks (id from file is not enforced to avoid sequence conflicts)
        rp_dir = base / "rulepacks"
        if rp_dir.exists():
            for p in rp_dir.glob("*.json"):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    if not isinstance(data, dict):
                        continue
                    org_id = data.get("org_id") or 1
                    name = data.get("name") or ""
                    obj = (
                        db.query(models.RulePack)
                        .filter(models.RulePack.org_id == org_id, models.RulePack.name == name)
                        .first()
                    )
                    if obj is None:
                        obj = models.RulePack(
                            org_id=org_id,
                            name=name,
                            rules=data.get("rules"),
                        )
                        setattr(obj, "version", data.get("version"))
                        db.add(obj)
                        db.commit()
                    else:
                        # Update in place
                        obj.rules = data.get("rules")
                        setattr(obj, "version", data.get("version"))
                        db.add(obj)
                        db.commit()
                except Exception:
                    continue
        # Anthropometrics (match by name/org; don't force id)
        an_dir = base / "anthropometrics"
        if an_dir.exists():
            for p in an_dir.glob("*.json"):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    org_id = data.get("org_id") or 1
                    name = data.get("name") or ""
                    obj = (
                        db.query(models.AnthropometricDataset)
                        .filter(models.AnthropometricDataset.org_id == org_id, models.AnthropometricDataset.name == name)
                        .first()
                    )
                    if obj is None:
                        obj = models.AnthropometricDataset(
                            org_id=org_id,
                            name=name,
                            source=data.get("source"),
                            schema=data.get("schema"),
                            distributions=data.get("distributions"),
                        )
                        db.add(obj)
                        db.commit()
                    else:
                        obj.source = data.get("source")
                        obj.schema = data.get("schema")
                        obj.distributions = data.get("distributions")
                        db.add(obj)
                        db.commit()
                except Exception:
                    continue
        # Abilities (match by name/org; don't force id)
        ab_dir = base / "abilities"
        if ab_dir.exists():
            for p in ab_dir.glob("*.json"):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    org_id = data.get("org_id") or 1
                    name = data.get("name") or ""
                    obj = (
                        db.query(models.AbilityProfile)
                        .filter(models.AbilityProfile.org_id == org_id, models.AbilityProfile.name == name)
                        .first()
                    )
                    if obj is None:
                        obj = models.AbilityProfile(
                            org_id=org_id,
                            name=name,
                            data=data.get("data"),
                        )
                        db.add(obj)
                        db.commit()
                    else:
                        obj.data = data.get("data")
                        db.add(obj)
                        db.commit()
                except Exception:
                    continue
