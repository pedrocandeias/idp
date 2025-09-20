from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..dependencies import get_current_user
from ..rbac import require_role
from ..schemas import RulePackCreate, RulePackRead

router = APIRouter(prefix="/api/v1/rulepacks", tags=["rulepacks"])


@router.get("", response_model=list[RulePackRead])
def list_rulepacks(current=Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(models.RulePack)
    if "superadmin" in (current.roles or []):
        items = q.all()
    else:
        items = q.filter(models.RulePack.org_id == current.org_id).all()
    return [RulePackRead.model_validate(x) for x in items]


@router.post("", response_model=RulePackRead, status_code=201)
def create_rulepack(
    payload: RulePackCreate,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current.org_id:
        raise HTTPException(status_code=400, detail="User not in an organization")
    require_role(
        current, ["org_admin", "researcher"]
    )  # allow org admin or researcher to create
    item = models.RulePack(
        org_id=current.org_id,
        name=payload.name,
        rules=payload.rules,
    )
    # add version pin
    setattr(item, "version", payload.version)
    db.add(item)
    db.commit()
    db.refresh(item)
    return RulePackRead.model_validate(item)


@router.get("/{pack_id}", response_model=RulePackRead)
def get_rulepack(
    pack_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    item = db.get(models.RulePack, pack_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    if "superadmin" not in (current.roles or []) and item.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return RulePackRead.model_validate(item)
