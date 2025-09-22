from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..dependencies import get_current_user
from ..rbac import require_role
from ..schemas import ProjectCreate, ProjectRead
from ..storage import presigned_get
from ..storage import delete_object
from ..schemas import UserRead

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


@router.get("/{project_id}/reports")
def list_reports(
    project_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    proj = db.get(models.Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Not found")
    if "superadmin" not in (current.roles or []) and proj.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    items = (
        db.query(models.Report)
        .filter(models.Report.project_id == project_id)
        .order_by(models.Report.id.desc())
        .all()
    )
    out = []
    for r in items:
        try:
            html_url = presigned_get(r.html_key) if r.html_key else None
        except Exception:
            html_url = None
        try:
            pdf_url = presigned_get(r.pdf_key) if r.pdf_key else None
        except Exception:
            pdf_url = None
        out.append(
            {
                "id": r.id,
                "project_id": r.project_id,
                "title": r.title,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "presigned_html_url": html_url,
                "presigned_pdf_url": pdf_url,
            }
        )
    return out

@router.delete("/{project_id}/reports/{report_id}", status_code=204)
def delete_report(
    project_id: int, report_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    proj = db.get(models.Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Not found")
    if "superadmin" not in (current.roles or []) and proj.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    rep = db.get(models.Report, report_id)
    if not rep or rep.project_id != project_id:
        raise HTTPException(status_code=404, detail="Not found")
    # delete objects if any
    try:
        if rep.html_key:
            delete_object(rep.html_key)
    except Exception:
        pass
    try:
        if rep.pdf_key:
            delete_object(rep.pdf_key)
    except Exception:
        pass
    db.delete(rep)
    db.commit()
    return None


@router.get("/{project_id}/evaluations")
def list_project_evaluations(
    project_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    proj = db.get(models.Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Not found")
    if "superadmin" not in (current.roles or []) and proj.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    scen_ids = [
        s.id
        for s in db.query(models.SimulationScenario).filter(models.SimulationScenario.project_id == project_id).all()
    ]
    if not scen_ids:
        return []
    runs = (
        db.query(models.EvaluationRun)
        .filter(models.EvaluationRun.scenario_id.in_(scen_ids))
        .order_by(models.EvaluationRun.id.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "scenario_id": r.scenario_id,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "metrics": r.metrics,
        }
        for r in runs
    ]


@router.get("/{project_id}/members", response_model=list[UserRead])
def list_members(project_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)):
    proj = db.get(models.Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Not found")
    if "superadmin" not in (current.roles or []) and proj.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    # join memberships to users
    mids = db.query(models.ProjectMembership).filter(models.ProjectMembership.project_id == project_id).all()
    user_ids = [m.user_id for m in mids]
    if not user_ids:
        return []
    users = db.query(models.User).filter(models.User.id.in_(user_ids)).all()
    return [UserRead.model_validate(u) for u in users]


@router.post("/{project_id}/members")
def add_member(project_id: int, payload: dict, current=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current, ["org_admin"])  # membership managed by org admin
    proj = db.get(models.Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Not found")
    if "superadmin" not in (current.roles or []) and proj.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    uid = payload.get("user_id")
    if not isinstance(uid, int):
        raise HTTPException(status_code=400, detail="user_id required")
    user = db.get(models.User, uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.org_id != proj.org_id:
        raise HTTPException(status_code=400, detail="User must be in same org")
    existing = db.query(models.ProjectMembership).filter(
        models.ProjectMembership.project_id == project_id,
        models.ProjectMembership.user_id == uid,
    ).first()
    if existing:
        return {"status": "ok", "added": False}
    db.add(models.ProjectMembership(project_id=project_id, user_id=uid))
    db.commit()
    return {"status": "ok", "added": True}


@router.delete("/{project_id}/members/{user_id}")
def remove_member(project_id: int, user_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current, ["org_admin"])  # membership managed by org admin
    proj = db.get(models.Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Not found")
    if "superadmin" not in (current.roles or []) and proj.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    m = db.query(models.ProjectMembership).filter(
        models.ProjectMembership.project_id == project_id,
        models.ProjectMembership.user_id == user_id,
    ).first()
    if not m:
        return {"status": "ok", "removed": False}
    db.delete(m)
    db.commit()
    return {"status": "ok", "removed": True}
