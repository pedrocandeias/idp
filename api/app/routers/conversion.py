from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..dependencies import get_current_user
from ..tasks import convert_artifact


router = APIRouter(prefix="/api/v1", tags=["conversion"])


@router.post("/artifacts/{artifact_id}/convert")
def request_conversion(
    artifact_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    art = db.get(models.DesignArtifact, artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")
    proj = db.get(models.Project, art.project_id)
    if "superadmin" not in (current.roles or []) and proj.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    convert_artifact.delay(artifact_id)
    return {"status": "queued"}

