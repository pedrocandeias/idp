from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..dependencies import get_current_user
from ..db import get_db
from .. import models
from ..schemas import AnthropometricDatasetCreate, AnthropometricDatasetRead
from ..services.datasets import query_percentile
from ..rbac import require_role


router = APIRouter(prefix="/api/v1/datasets/anthropometrics", tags=["datasets:anthropometrics"])


@router.get("", response_model=list[AnthropometricDatasetRead])
def list_anthro(current=Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(models.AnthropometricDataset)
    if "superadmin" in (current.roles or []):
        items = q.all()
    else:
        items = q.filter(models.AnthropometricDataset.org_id == current.org_id).all()
    return [AnthropometricDatasetRead.model_validate(x) for x in items]


@router.post("", response_model=AnthropometricDatasetRead, status_code=201)
def create_anthro(payload: AnthropometricDatasetCreate, current=Depends(get_current_user), db: Session = Depends(get_db)):
    if not current.org_id:
        raise HTTPException(status_code=400, detail="User not in an organization")
    require_role(current, ["org_admin", "researcher"])  # dataset create
    item = models.AnthropometricDataset(
        org_id=current.org_id,
        name=payload.name,
        source=payload.source,
        schema=payload.schema,
        distributions=payload.distributions,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return AnthropometricDatasetRead.model_validate(item)


@router.get("/{dataset_id}/percentile")
def get_percentile(
    dataset_id: int,
    metric: str = Query(...),
    percentile: float = Query(..., ge=0, le=100),
    region: str | None = Query(default=None),
    sex: str | None = Query(default=None),
    age: str | None = Query(default=None),
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ds = db.get(models.AnthropometricDataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if "superadmin" not in (current.roles or []) and ds.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not ds.distributions:
        raise HTTPException(status_code=400, detail="Dataset has no distributions")
    try:
        value = query_percentile(ds.distributions, metric, percentile, region=region, sex=sex, age=age)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"metric": metric, "percentile": percentile, "value": value}
