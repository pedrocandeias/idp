from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..dependencies import get_current_user
from ..rbac import require_role
from ..storage import get_s3_client
from ..config import settings

router = APIRouter(prefix="/api/v1/files", tags=["files"])


def _project_id_from_key(key: str) -> int | None:
    # Expected keys: projects/{project_id}/...
    parts = key.split("/")
    if len(parts) >= 2 and parts[0] == "projects":
        try:
            return int(parts[1])
        except Exception:
            return None
    return None


@router.get("/get")
def proxy_get_object(key: str, current=Depends(get_current_user), db: Session = Depends(get_db)):
    # Basic authorization: user must belong to the project's org
    pid = _project_id_from_key(key)
    if pid is None:
        raise HTTPException(status_code=400, detail="Invalid key format")
    proj = db.get(models.Project, pid)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    if "superadmin" not in (current.roles or []) and proj.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    s3 = get_s3_client()
    try:
        obj = s3.get_object(Bucket=settings.s3_bucket, Key=key)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    data = obj["Body"].read()
    ctype = obj.get("ContentType") or "application/octet-stream"
    return Response(content=data, media_type=ctype)

