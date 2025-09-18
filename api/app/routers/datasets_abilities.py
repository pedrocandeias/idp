from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..dependencies import get_current_user
from ..db import get_db
from .. import models
from ..schemas import AbilityProfileRead, AbilityProfileCreate


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
def create_ability(payload: AbilityProfileCreate, current=Depends(get_current_user), db: Session = Depends(get_db)):
    if not current.org_id:
        raise HTTPException(status_code=400, detail="User not in an organization")
    item = models.AbilityProfile(
        org_id=current.org_id,
        name=payload.name,
        data=payload.data,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return AbilityProfileRead.model_validate(item)

