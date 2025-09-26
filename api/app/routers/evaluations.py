from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..db import get_db
from ..dependencies import get_current_user
from ..rbac import require_role
from ..reporting import render_html, render_pdf, sha256_bytes
from ..storage import get_s3_client, presigned_get, upload_bytes
from ..tasks import run_evaluation

router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])


@router.post("", status_code=202)
def enqueue_evaluation(
    payload: dict, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    def _as_int(val: Any, name: str) -> int:
        try:
            return int(val)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid {name}") from exc

    artifact_id = _as_int(payload.get("artifact_id"), "artifact_id")
    scenario_id = _as_int(payload.get("scenario_id"), "scenario_id")
    rulepack_id = _as_int(payload.get("rulepack_id"), "rulepack_id")
    webhook_url = payload.get("webhook_url")
    debug = bool(payload.get("debug", False))

    scenario = db.get(models.SimulationScenario, scenario_id)
    rulepack = db.get(models.RulePack, rulepack_id)
    artifact = db.get(models.DesignArtifact, artifact_id)
    if not all([scenario, rulepack, artifact]):
        raise HTTPException(status_code=400, detail="Invalid references")
    # scope org
    if "superadmin" not in (current.roles or []) and scenario and scenario.id:
        # We ensure project/org match user
        project = db.get(models.Project, scenario.project_id)
        if not project or project.org_id != current.org_id:
            raise HTTPException(status_code=403, detail="Forbidden")

    require_role(current, ["org_admin", "researcher", "designer"])  # can submit eval
    run = models.EvaluationRun(
        scenario_id=scenario_id,
        status="queued",
        metrics={
            "artifact_id": artifact_id,
            "rulepack_id": rulepack_id,
            "webhook_url": webhook_url,
            "scenario_id": scenario_id,
            "debug": debug,
            "log": [] if debug else None,
        },
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    run_evaluation.delay(run.id)
    return {"id": run.id, "status": run.status}


@router.get("/{evaluation_id}")
def get_evaluation(
    evaluation_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    run = db.get(models.EvaluationRun, evaluation_id)
    if not run:
        raise HTTPException(status_code=404, detail="Not found")
    # scope
    scen = db.get(models.SimulationScenario, run.scenario_id)
    proj = db.get(models.Project, scen.project_id) if scen else None
    if "superadmin" not in (current.roles or []) and (
        not proj or proj.org_id != current.org_id
    ):
        raise HTTPException(status_code=403, detail="Forbidden")
    return {
        "id": run.id,
        "status": run.status,
        "metrics": run.metrics,
        "results": getattr(run, "results_json", None),
        "inclusivity_index": getattr(run, "inclusivity_index_json", None),
    }


@router.post("/{evaluation_id}/report")
def create_report(
    evaluation_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    run = db.get(models.EvaluationRun, evaluation_id)
    if not run or run.status != "done":
        raise HTTPException(status_code=400, detail="Evaluation not ready")

    scenario = db.get(models.SimulationScenario, run.scenario_id)
    project = db.get(models.Project, scenario.project_id) if scenario else None
    # find artifact and rulepack ids from metrics
    m = run.metrics or {}
    artifact = (
        db.get(models.DesignArtifact, m.get("artifact_id"))
        if m.get("artifact_id")
        else None
    )
    rulepack = (
        db.get(models.RulePack, m.get("rulepack_id")) if m.get("rulepack_id") else None
    )

    # authorize org scope
    if "superadmin" not in (current.roles or []) and (
        not project or project.org_id != current.org_id
    ):
        raise HTTPException(status_code=403, detail="Forbidden")
    # previous run delta
    prev = (
        db.query(models.EvaluationRun)
        .filter(
            models.EvaluationRun.scenario_id == run.scenario_id,
            models.EvaluationRun.id < run.id,
        )
        .order_by(models.EvaluationRun.id.desc())
        .first()
    )
    delta = None
    try:
        prev_score = (prev.inclusivity_index_json or {}).get("score") if prev else None
        cur_score = (run.inclusivity_index_json or {}).get("score")
        if prev_score is not None and cur_score is not None:
            delta = float(cur_score) - float(prev_score)
    except Exception:
        delta = None

    context = {
        "run": run,
        "project": project,
        "scenario": scenario,
        "artifact": artifact,
        "rulepack": rulepack,
        "results": run.results_json or {"rules": []},
        "index": run.inclusivity_index_json
        or {
            "score": 0,
            "components": {"reach": False, "strength": False, "visual": False},
        },
        "delta": delta,
        "date": run.completed_at.isoformat() if run.completed_at else "",
        "checksum": "",
    }

    html = render_html(context)
    pdf = render_pdf(html)
    checksum = sha256_bytes(pdf)
    context["checksum"] = checksum
    # re-render HTML with checksum visible
    html = render_html(context)
    pdf = render_pdf(html)
    checksum = sha256_bytes(pdf)

    # Upload
    client = get_s3_client()
    base = f"projects/{project.id}/reports/{run.id}"
    html_key = f"{base}.html"
    pdf_key = f"{base}.pdf"
    upload_bytes(html_key, html.encode("utf-8"), "text/html", client=client)
    upload_bytes(pdf_key, pdf, "application/pdf", client=client)

    report = models.Report(
        project_id=project.id,
        title=f"Evaluation Report #{run.id}",
        content=None,
        html_key=html_key,
        pdf_key=pdf_key,
        checksum_sha256=checksum,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Build URLs, preferring presigned; fallback to API proxy
    proxy_html = f"/api/v1/files/get?key={html_key}"
    proxy_pdf = f"/api/v1/files/get?key={pdf_key}"
    try:
        html_url = presigned_get(html_key)
    except Exception:
        html_url = proxy_html
    try:
        pdf_url = presigned_get(pdf_key)
    except Exception:
        pdf_url = proxy_pdf

    return {
        "id": report.id,
        "project_id": report.project_id,
        "title": report.title,
        "content": report.content,
        "html_key": report.html_key,
        "pdf_key": report.pdf_key,
        "checksum_sha256": report.checksum_sha256,
        "presigned_html_url": html_url,
        "presigned_pdf_url": pdf_url,
    }


@router.delete("/{evaluation_id}")
def delete_evaluation(
    evaluation_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)
):
    run = db.get(models.EvaluationRun, evaluation_id)
    if not run:
        raise HTTPException(status_code=404, detail="Not found")
    scen = db.get(models.SimulationScenario, run.scenario_id)
    proj = db.get(models.Project, scen.project_id) if scen else None
    if "superadmin" not in (current.roles or []) and (
        not proj or proj.org_id != current.org_id
    ):
        raise HTTPException(status_code=403, detail="Forbidden")
    require_role(current, ["org_admin", "researcher"])  # destructive
    db.delete(run)
    db.commit()
    return {"status": "ok", "deleted": True, "id": evaluation_id}
