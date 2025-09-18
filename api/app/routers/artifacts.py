from __future__ import annotations

import json
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from ..dependencies import get_current_user
from ..db import get_db
from .. import models
from ..schemas import DesignArtifactRead
from ..storage import upload_bytes, presigned_get, presigned_put, new_object_key, get_s3_client
from ..config import settings
from ..rbac import require_role


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
            metadata=None,
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
        if len(pdata) > 5 * 1024 * 1024:
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

    url = presigned_get(object_key, client=client)

    resp = DesignArtifactRead.model_validate(art)
    resp.presigned_url = url
    return resp
