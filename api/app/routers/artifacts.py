from __future__ import annotations

import json
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..db import get_db
from ..dependencies import get_current_user
from ..rbac import require_role
from ..schemas import DesignArtifactRead
from ..storage import (
    get_s3_client,
    new_object_key,
    presigned_get,
    presigned_put,
    delete_object,
    upload_bytes,
)

router = APIRouter(prefix="/api/v1/projects/{project_id}/artifacts", tags=["artifacts"])


ALLOWED_EXTS = {"gltf", "glb", "stp", "step"}
MIME_BY_EXT = {
    "gltf": "model/gltf+json",
    "glb": "model/gltf-binary",
    "stp": "application/step",
    "step": "application/step",
}


def _ext_from_filename(name: str) -> str:
    return name.rsplit(".", 1)[1].lower() if "." in name else ""


@router.post("")
def upload_artifact(
    project_id: int,
    file: UploadFile = File(None),
    params: UploadFile | None = File(default=None),
    name: str | None = Form(default=None),
    type: str | None = Form(default=None),
    presign: bool = Form(default=False),
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
) -> DesignArtifactRead:
    # Validate project & scope
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if "superadmin" not in (current.roles or []) and project.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    require_role(current, ["org_admin", "designer"])  # upload requires edit role

    if presign:
        if not name:
            raise HTTPException(status_code=400, detail="name required for presign")
        ext = _ext_from_filename(name)
        if ext not in ALLOWED_EXTS:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        key = new_object_key(project_id, name)
        url = presigned_put(key, MIME_BY_EXT.get(ext))
        get_url = presigned_get(key)
        return DesignArtifactRead(
            id=0,
            project_id=project_id,
            name=name,
            type=type,
            uri=None,
            meta=None,
            object_key=key,
            params_key=None,
            object_mime=MIME_BY_EXT.get(ext),
            size_bytes=None,
            presigned_url=get_url,
        )

    if file is None:
        raise HTTPException(status_code=400, detail="file is required")

    filename = file.filename or "upload.bin"
    ext = _ext_from_filename(filename)
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Enforce size limit
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = file.file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    params_key: str | None = None
    if params is not None:
        pdata = params.file.read()
        if len(pdata) > settings.max_params_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Params too large")
        # Validate JSON
        try:
            json.loads(pdata.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid params JSON")

    object_key = new_object_key(project_id, filename)
    object_mime = MIME_BY_EXT.get(ext, file.content_type or "application/octet-stream")

    client = get_s3_client()
    upload_bytes(object_key, content, object_mime, client=client)

    if params is not None:
        params_key = object_key.rsplit(".", 1)[0] + ".json"
        upload_bytes(params_key, pdata, "application/json", client=client)

    art = models.DesignArtifact(
        project_id=project_id,
        name=name or filename,
        type=type or ext,
        uri=f"s3://{settings.s3_bucket}/{object_key}",
        object_key=object_key,
        params_key=params_key,
        object_mime=object_mime,
        size_bytes=len(content),
    )
    db.add(art)
    db.commit()
    db.refresh(art)

    # Generate a browser-reachable URL (uses public endpoint)
    url = presigned_get(object_key)

    resp = DesignArtifactRead.model_validate(art)
    resp.presigned_url = url
    return resp


@router.get("")
def list_artifacts(
    project_id: int,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
) -> list[DesignArtifactRead]:
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if "superadmin" not in (current.roles or []) and project.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    items = (
        db.query(models.DesignArtifact)
        .filter(models.DesignArtifact.project_id == project_id)
        .order_by(models.DesignArtifact.id.desc())
        .all()
    )
    out: list[DesignArtifactRead] = []
    for a in items:
        resp = DesignArtifactRead.model_validate(a)
        if a.object_key:
            try:
                # Use public endpoint for browser access
                resp.presigned_url = presigned_get(a.object_key)
            except Exception:
                resp.presigned_url = None
        out.append(resp)
    return out


# Common artifact routes (by id)
router_common = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])


@router_common.get("/{artifact_id}")
def get_artifact_by_id(
    artifact_id: int,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
) -> DesignArtifactRead:
    art = db.get(models.DesignArtifact, artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="Not found")
    proj = db.get(models.Project, art.project_id)
    if "superadmin" not in (current.roles or []) and proj.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    resp = DesignArtifactRead.model_validate(art)
    if art.object_key:
        try:
            resp.presigned_url = presigned_get(art.object_key)
        except Exception:
            resp.presigned_url = None
    return resp


@router.delete("/{artifact_id}", status_code=204)
def delete_artifact(
    project_id: int,
    artifact_id: int,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    art = db.get(models.DesignArtifact, artifact_id)
    if not art or art.project_id != project_id:
        raise HTTPException(status_code=404, detail="Not found")
    # scope check
    proj = db.get(models.Project, project_id)
    if "superadmin" not in (current.roles or []) and proj.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    require_role(current, ["org_admin", "designer"])  # delete allowed to editors
    # delete objects if present
    client = get_s3_client()
    if art.object_key:
        delete_object(art.object_key, client=client)
    if art.params_key:
        delete_object(art.params_key, client=client)
    db.delete(art)
    db.commit()
    return None
