from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..dependencies import get_current_user
from ..rbac import require_role
from ..schemas import AbilityProfileCreate, AbilityProfileRead
from ..persistence import save_ability_json, delete_ability_json

router = APIRouter(prefix="/api/v1/datasets/abilities", tags=["datasets:abilities"])


@router.get("", response_model=list[AbilityProfileRead])
def list_abilities(current=Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(models.AbilityProfile)
    if "superadmin" in (current.roles or []):
        items = q.all()
    else:
        items = q.filter(models.AbilityProfile.org_id == current.org_id).all()
    return [AbilityProfileRead.model_validate(x) for x in items]


@router.post("", response_model=AbilityProfileRead, status_code=201)
def create_ability(
    payload: AbilityProfileCreate,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current.org_id:
        raise HTTPException(status_code=400, detail="User not in an organization")
    require_role(current, ["org_admin", "researcher"])  # abilities create
    item = models.AbilityProfile(
        org_id=current.org_id,
        name=payload.name,
        data=payload.data,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    try:
        save_ability_json(item)
    except Exception:
        pass
    return AbilityProfileRead.model_validate(item)


@router.get("/{ability_id}", response_model=AbilityProfileRead)
def get_ability(
    ability_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    item = db.get(models.AbilityProfile, ability_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    if "superadmin" not in (current.roles or []) and item.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return AbilityProfileRead.model_validate(item)


@router.delete("/{ability_id}", status_code=204)
def delete_ability(
    ability_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    item = db.get(models.AbilityProfile, ability_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    if "superadmin" not in (current.roles or []) and item.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    require_role(current, ["org_admin", "researcher"])  # destructive
    db.delete(item)
    db.commit()
    try:
        delete_ability_json(ability_id)
    except Exception:
        pass
    return None


@router.patch("/{ability_id}", response_model=AbilityProfileRead)
def update_ability(
    ability_id: int,
    payload: dict,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.get(models.AbilityProfile, ability_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    if "superadmin" not in (current.roles or []) and item.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    require_role(current, ["org_admin", "researcher"])  # update
    name = payload.get('name')
    if isinstance(name, str):
        item.name = name
    data = payload.get('data')
    if data is not None:
        item.data = data
    db.add(item)
    db.commit()
    db.refresh(item)
    try:
        save_ability_json(item)
    except Exception:
        pass
    return AbilityProfileRead.model_validate(item)
