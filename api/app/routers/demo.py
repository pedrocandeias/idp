from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..dependencies import get_current_user
from ..rbac import require_role
from ..schemas import ProjectRead
from ..storage import get_s3_client, new_object_key, upload_bytes
from ..tasks import run_evaluation


router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


@router.post("/seed")
def seed_demo(current=Depends(get_current_user), db: Session = Depends(get_db)):
    # Require a basic role
    require_role(current, ["designer", "researcher", "org_admin"])  # default user has designer

    # 1) Ensure a project exists in user's org
    if not current.org_id:
        raise HTTPException(status_code=400, detail="User not in an organization")
    proj = (
        db.query(models.Project)
        .filter(models.Project.org_id == current.org_id, models.Project.name == "Demo Project")
        .first()
    )
    if not proj:
        proj = models.Project(org_id=current.org_id, name="Demo Project", description="Demo")
        db.add(proj)
        db.commit()
        db.refresh(proj)

    # 2) Upload a minimal artifact from seeds
    seeds_dir = Path(__file__).resolve().parents[2] / "seeds"
    gltf_path = seeds_dir / "minimal.gltf"
    if not gltf_path.exists():
        raise HTTPException(status_code=500, detail="Demo asset missing")

    object_key = new_object_key(proj.id, "minimal.gltf")
    client = get_s3_client()
    data = gltf_path.read_bytes()
    upload_bytes(object_key, data, "model/gltf+json", client=client)

    from ..config import settings
    art = models.DesignArtifact(
        project_id=proj.id,
        name="Minimal glTF",
        type="gltf",
        uri=f"s3://{settings.s3_bucket}/{object_key}",
        object_key=object_key,
        params_key=None,
        object_mime="model/gltf+json",
        size_bytes=len(data),
    )
    db.add(art)
    db.commit()
    db.refresh(art)

    # 3) Create or find a scenario
    scen = (
        db.query(models.SimulationScenario)
        .filter(models.SimulationScenario.project_id == proj.id, models.SimulationScenario.name == "Demo Scenario")
        .first()
    )
    if not scen:
        scen = models.SimulationScenario(
            project_id=proj.id,
            name="Demo Scenario",
            config={
                "distance_to_control_cm": 50,
                "fg_rgb": [255, 255, 255],
                "bg_rgb": [0, 0, 0],
                "required_force_N": 15,
                "capability_N": 20,
            },
        )
        db.add(scen)
        db.commit()
        db.refresh(scen)

    # 4) Create or find a rulepack from seeds
    rp = (
        db.query(models.RulePack)
        .filter(models.RulePack.org_id == proj.org_id, models.RulePack.name == "General EU v1")
        .first()
    )
    if not rp:
        rp_path = seeds_dir / "rulepack_general_eu_v1.json"
        if not rp_path.exists():
            raise HTTPException(status_code=500, detail="Demo rulepack missing")
        payload = json.loads(rp_path.read_text("utf-8"))
        rp = models.RulePack(
            org_id=proj.org_id, name=payload.get("name", "General EU v1"), rules=payload.get("rules")
        )
        setattr(rp, "version", payload.get("version", "1.0.0"))
        db.add(rp)
        db.commit()
        db.refresh(rp)

    # 5) Enqueue evaluation
    run = models.EvaluationRun(
        scenario_id=scen.id,
        status="queued",
        metrics={"artifact_id": art.id, "rulepack_id": rp.id, "scenario_id": scen.id},
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    run_evaluation.delay(run.id)

    return {
        "project_id": proj.id,
        "artifact_id": art.id,
        "scenario_id": scen.id,
        "rulepack_id": rp.id,
        "evaluation_id": run.id,
    }
