from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..dependencies import get_current_user
from ..rbac import require_role
from ..schemas import SimulationScenarioCreate, SimulationScenarioRead


router = APIRouter(prefix="/api/v1/scenarios", tags=["scenarios"])


@router.post("", response_model=SimulationScenarioRead, status_code=201)
def create_scenario(
    payload: SimulationScenarioCreate,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate project exists and belongs to user's org (unless superadmin)
    project = db.get(models.Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=400, detail="Invalid project_id")
    if "superadmin" not in (current.roles or []) and project.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    require_role(current, ["org_admin", "designer", "researcher"])  # can create

    scen = models.SimulationScenario(
        project_id=payload.project_id,
        name=payload.name,
        config=payload.config,
    )
    db.add(scen)
    db.commit()
    db.refresh(scen)
    return SimulationScenarioRead.model_validate(scen)


@router.get("/{scenario_id}", response_model=SimulationScenarioRead)
def get_scenario(
    scenario_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    scen = db.get(models.SimulationScenario, scenario_id)
    if not scen:
        raise HTTPException(status_code=404, detail="Not found")
    proj = db.get(models.Project, scen.project_id)
    if "superadmin" not in (current.roles or []) and (
        not proj or proj.org_id != current.org_id
    ):
        raise HTTPException(status_code=403, detail="Forbidden")
    return SimulationScenarioRead.model_validate(scen)


@router.get("", response_model=list[SimulationScenarioRead])
def list_scenarios(
    project_id: int | None = Query(default=None),
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(models.SimulationScenario)
    if project_id is not None:
        # validate access to project
        proj = db.get(models.Project, project_id)
        if not proj:
            raise HTTPException(status_code=400, detail="Invalid project_id")
        if "superadmin" not in (current.roles or []) and proj.org_id != current.org_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        items = q.filter(models.SimulationScenario.project_id == project_id).all()
    else:
        # list all scenarios in user's org by joining via project
        if "superadmin" in (current.roles or []):
            items = q.all()
        else:
            # get projects for org
            proj_ids = [
                p.id
                for p in db.query(models.Project)
                .filter(models.Project.org_id == current.org_id)
                .all()
            ]
            if proj_ids:
                items = q.filter(models.SimulationScenario.project_id.in_(proj_ids)).all()
            else:
                items = []
    return [SimulationScenarioRead.model_validate(s) for s in items]


@router.delete("/{scenario_id}", status_code=204)
def delete_scenario(
    scenario_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    scen = db.get(models.SimulationScenario, scenario_id)
    if not scen:
        raise HTTPException(status_code=404, detail="Not found")
    proj = db.get(models.Project, scen.project_id)
    if "superadmin" not in (current.roles or []) and (
        not proj or proj.org_id != current.org_id
    ):
        raise HTTPException(status_code=403, detail="Forbidden")
    require_role(current, ["org_admin", "designer"])  # allow delete by org admin/designer
    db.delete(scen)
    db.commit()
    return None
