from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..dependencies import get_current_user
from ..rbac import require_role
from ..schemas import AnthropometricDatasetCreate, AnthropometricDatasetRead
from ..persistence import save_anthro_json, delete_anthro_json
from ..services.datasets import query_percentile

router = APIRouter(
    prefix="/api/v1/datasets/anthropometrics", tags=["datasets:anthropometrics"]
)


@router.get("", response_model=list[AnthropometricDatasetRead])
def list_anthro(current=Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(models.AnthropometricDataset)
    if "superadmin" in (current.roles or []):
        items = q.all()
    else:
        items = q.filter(models.AnthropometricDataset.org_id == current.org_id).all()
    return [AnthropometricDatasetRead.model_validate(x) for x in items]


@router.post("", response_model=AnthropometricDatasetRead, status_code=201)
def create_anthro(
    payload: AnthropometricDatasetCreate,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
    try:
        save_anthro_json(item)
    except Exception:
        pass
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
        value = query_percentile(
            ds.distributions, metric, percentile, region=region, sex=sex, age=age
        )
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"metric": metric, "percentile": percentile, "value": value}


@router.get("/{dataset_id}", response_model=AnthropometricDatasetRead)
def get_anthro_dataset(
    dataset_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    ds = db.get(models.AnthropometricDataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if "superadmin" not in (current.roles or []) and ds.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return AnthropometricDatasetRead.model_validate(ds)


@router.delete("/{dataset_id}", status_code=204)
def delete_anthro_dataset(
    dataset_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    ds = db.get(models.AnthropometricDataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if "superadmin" not in (current.roles or []) and ds.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    require_role(current, ["org_admin", "researcher"])  # destructive
    db.delete(ds)
    db.commit()
    try:
        delete_anthro_json(dataset_id)
    except Exception:
        pass
    return None


@router.patch("/{dataset_id}", response_model=AnthropometricDatasetRead)
def update_anthro_dataset(
    dataset_id: int,
    payload: dict,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ds = db.get(models.AnthropometricDataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if "superadmin" not in (current.roles or []) and ds.org_id != current.org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    require_role(current, ["org_admin", "researcher"])  # update
    name = payload.get("name")
    if isinstance(name, str):
        ds.name = name
    src = payload.get("source")
    if isinstance(src, str) or src is None:
        ds.source = src
    schema = payload.get("schema")
    if schema is not None:
        ds.schema = schema
    distributions = payload.get("distributions")
    if distributions is not None:
        ds.distributions = distributions
    db.add(ds)
    db.commit()
    db.refresh(ds)
    try:
        save_anthro_json(ds)
    except Exception:
        pass
    return AnthropometricDatasetRead.model_validate(ds)
