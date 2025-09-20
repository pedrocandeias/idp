from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..dependencies import get_current_user
from ..rbac import require_role
from ..schemas import OrganizationCreate, OrganizationRead

router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationRead, status_code=201)
def create_org(
    payload: OrganizationCreate,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationRead:
    require_role(current, ["superadmin"])  # only superadmin can create orgs
    existing = db.query(models.Org).filter(models.Org.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Organization already exists")
    org = models.Org(name=payload.name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return OrganizationRead.model_validate(org)


@router.get("", response_model=list[OrganizationRead])
def list_orgs(current=Depends(get_current_user), db: Session = Depends(get_db)):
    # Scoped: non-superadmin sees only their org
    if current and "superadmin" in (current.roles or []):
        orgs = db.query(models.Org).all()
    else:
        orgs = db.query(models.Org).filter(models.Org.id == current.org_id).all()
    return [OrganizationRead.model_validate(o) for o in orgs]


@router.get("/{org_id}", response_model=OrganizationRead)
def get_org(
    org_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    org = db.get(models.Org, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Not found")
    if "superadmin" not in (current.roles or []) and current.org_id != org.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return OrganizationRead.model_validate(org)


@router.patch("/{org_id}", response_model=OrganizationRead)
def update_org(
    org_id: int,
    payload: OrganizationCreate,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org = db.get(models.Org, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Not found")
    require_role(
        current, ["superadmin", "org_admin"]
    )  # must be admin of own org or superadmin
    if "superadmin" not in (current.roles or []) and current.org_id != org.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    org.name = payload.name
    db.add(org)
    db.commit()
    db.refresh(org)
    return OrganizationRead.model_validate(org)


@router.delete("/{org_id}", status_code=204)
def delete_org(
    org_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    org = db.get(models.Org, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Not found")
    require_role(current, ["superadmin"])  # destructive op: superadmin only
    if "superadmin" not in (current.roles or []) and current.org_id != org.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    db.delete(org)
    db.commit()
    return None
