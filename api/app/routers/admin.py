from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..db import get_db


router = APIRouter(prefix="/api/v1/admin", tags=["admin"], include_in_schema=True)


@router.post("/bootstrap_superadmin")
def bootstrap_superadmin(payload: dict, db: Session = Depends(get_db)):
    secret = payload.get("secret")
    email = payload.get("email")
    if not settings.bootstrap_superadmin_secret:
        raise HTTPException(status_code=403, detail="Bootstrap disabled")
    if not secret or secret != settings.bootstrap_superadmin_secret:
        raise HTTPException(status_code=403, detail="Invalid secret")
    if not email:
        raise HTTPException(status_code=400, detail="email required")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    roles = set(user.roles or [])
    roles.add("superadmin")
    user.roles = list(roles)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "roles": user.roles}

