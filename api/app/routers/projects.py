from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..dependencies import get_current_user
from ..rbac import require_role
from ..schemas import ProjectCreate, ProjectRead

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(
    payload: ProjectCreate,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_role(current, ["org_admin", "designer"])  # create requires designer/admin
    if not current.org_id:
        raise HTTPException(status_code=400, detail="User not in an organization")
    proj = models.Project(
        org_id=current.org_id, name=payload.name, description=payload.description
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return ProjectRead.model_validate(proj)


@router.get("", response_model=list[ProjectRead])
def list_projects(current=Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(models.Project)
    if "superadmin" in (current.roles or []):
        projs = q.all()
    else:
        projs = q.filter(models.Project.org_id == current.org_id).all()
    return [ProjectRead.model_validate(p) for p in projs]


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    proj = db.get(models.Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Not found")
    if "superadmin" not in (current.roles or []) and proj.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return ProjectRead.model_validate(proj)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    payload: ProjectCreate,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_role(current, ["org_admin", "designer"])  # update requires editor role
    proj = db.get(models.Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Not found")
    if "superadmin" not in (current.roles or []) and proj.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    proj.name = payload.name
    proj.description = payload.description
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return ProjectRead.model_validate(proj)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    require_role(current, ["org_admin"])  # delete requires org admin
    proj = db.get(models.Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Not found")
    if "superadmin" not in (current.roles or []) and proj.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    db.delete(proj)
    db.commit()
    return None
