from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..dependencies import get_current_user
from ..rbac import require_role
from ..schemas import UserRead
from ..security import hash_password


router = APIRouter(prefix="/api/v1", tags=["users"])


@router.get("/me", response_model=UserRead)
def get_me(current=Depends(get_current_user)):
    return UserRead.model_validate(current)


@router.get("/users", response_model=list[UserRead])
def list_users(current=Depends(get_current_user), db: Session = Depends(get_db)):
    # org_admin can list users in their org; superadmin lists all
    if "superadmin" in (current.roles or []):
        users = db.query(models.User).all()
    else:
        require_role(current, ["org_admin"])  # must be org admin to list
        users = db.query(models.User).filter(models.User.org_id == current.org_id).all()
    return [UserRead.model_validate(u) for u in users]


@router.patch("/users/{user_id}/roles", response_model=UserRead)
def set_roles(user_id: int, payload: dict, current=Depends(get_current_user), db: Session = Depends(get_db)):
    # payload: {roles: [..]}
    roles = payload.get("roles")
    if not isinstance(roles, list):
        raise HTTPException(status_code=400, detail="roles must be a list")
    target = db.get(models.User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    # superadmin can set any; org_admin can modify users in their org (not superadmin)
    if "superadmin" in (current.roles or []):
        pass
    else:
        require_role(current, ["org_admin"])  # must be org_admin
        if target.org_id != current.org_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    target.roles = roles
    db.add(target)
    db.commit()
    db.refresh(target)
    return UserRead.model_validate(target)


@router.patch("/users/{user_id}/password")
def reset_password(user_id: int, payload: dict, current=Depends(get_current_user), db: Session = Depends(get_db)):
    new_password = payload.get("password")
    if not new_password:
        raise HTTPException(status_code=400, detail="password required")
    target = db.get(models.User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    # superadmin can reset any; org_admin can reset within their org
    if "superadmin" not in (current.roles or []):
        require_role(current, ["org_admin"])  # must be org_admin
        if target.org_id != current.org_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    target.hashed_password = hash_password(new_password)
    db.add(target)
    db.commit()
    return {"status": "ok"}


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)):
    target = db.get(models.User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    # prevent deleting self accidentally
    if current.id == target.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    # authz
    if "superadmin" not in (current.roles or []):
        require_role(current, ["org_admin"])  # org admin only within org
        if target.org_id != current.org_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    # Null references in audit log to keep FK happy, then delete
    db.query(models.AuditEvent).filter(models.AuditEvent.user_id == target.id).update({models.AuditEvent.user_id: None})
    db.delete(target)
    db.commit()
    return None
