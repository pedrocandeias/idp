from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
import traceback
from typing import Any, Dict

import requests
from sqlalchemy.orm import Session

from . import models
from .celery_app import celery_app
from .db import SessionLocal
from .rules import evaluate_rule, UnsafeExpression
from .storage import upload_bytes, new_object_key
from .simulations import (
    inclusivity_index,
    reach_envelope_ok,
    strength_feasible,
    wcag_contrast_from_rgb,
)

logger = logging.getLogger(__name__)


def _load_entities(db: Session, evaluation_id: int):
    run = db.get(models.EvaluationRun, evaluation_id)
    if not run:
        raise RuntimeError("EvaluationRun not found")
    scenario = db.get(models.SimulationScenario, run.scenario_id)
    rulepack = (
        db.get(models.RulePack, run.metrics.get("rulepack_id")) if run.metrics else None
    )
    artifact = (
        db.get(models.DesignArtifact, run.metrics.get("artifact_id"))
        if run.metrics
        else None
    )
    return run, scenario, rulepack, artifact


@celery_app.task(name="app.tasks.run_evaluation")
def run_evaluation(evaluation_id: int) -> Dict[str, Any]:
    logger.info(f"Starting evaluation {evaluation_id}")
    with SessionLocal() as db:
        run, scenario, rulepack, artifact = _load_entities(db, evaluation_id)
        run.status = "running"
        db.add(run)
        db.commit()

        debug = bool((run.metrics or {}).get("debug"))
        def dbg(msg: str) -> None:
            try:
                if debug:
                    run.metrics.setdefault("log", []).append({
                        "t": datetime.now(timezone.utc).isoformat(),
                        "msg": msg,
                    })
            except Exception:
                pass
            logger.info(msg)

        try:
            # Simulations (very simplified, pull inputs from scenario.config or defaults)
            cfg = (scenario.config or {}) if scenario else {}
            distance_cm = float(cfg.get("distance_to_control_cm", 55.0))
            posture = str(cfg.get("posture", "seated"))
            required_force_N = float(cfg.get("required_force_N", 20.0))
            capability_N = float(cfg.get("capability_N", 25.0))
            fg_rgb = tuple(cfg.get("fg_rgb", [255, 255, 255]))
            bg_rgb = tuple(cfg.get("bg_rgb", [0, 0, 0]))

            dbg("Sim: reach envelope check ...")
            reach_ok = reach_envelope_ok(distance_cm, posture)
            dbg("Sim: strength feasibility ...")
            strength_ok = strength_feasible(required_force_N, capability_N)
            dbg("Sim: visual contrast ...")
            contrast = wcag_contrast_from_rgb(fg_rgb, bg_rgb)
            visual_ok = contrast >= 4.5

            # Rules evaluation
            dbg("Evaluating rules ...")
            per_rule = []
            rule_debug = [] if debug else None
            if rulepack and (rulepack.rules or {}).get("rules"):
                for rule in rulepack.rules["rules"]:
                    # Provide a variable set drawn from scenario with common aliases
                    base_w = float(cfg.get("button_w_mm", cfg.get("w_mm", cfg.get("w", 10))))
                    base_h = float(cfg.get("button_h_mm", cfg.get("h_mm", cfg.get("h", 10))))
                    inputs = {
                        # generic environment metrics
                        "distance_cm": distance_cm,
                        "required_force_N": required_force_N,
                        "contrast_ratio": contrast,
                        # width/height aliases commonly used across rulepacks
                        "w": base_w,
                        "h": base_h,
                        "w_mm": base_w,
                        "h_mm": base_h,
                        "button_w_mm": base_w,
                        "button_h_mm": base_h,
                        "button_width_mm": base_w,
                        "button_height_mm": base_h,
                    }
                    # If specific variables are requested by the rule, try config overrides
                    for var in (rule.get("variables") or []):
                        if var in cfg:
                            try:
                                inputs[var] = float(cfg[var]) if isinstance(cfg[var], (int, float, str)) else cfg[var]
                            except Exception:
                                inputs[var] = cfg[var]
                    try:
                        res = evaluate_rule(rule, inputs)
                        per_rule.append({
                            "id": res.id,
                            "passed": res.passed,
                            "severity": res.severity,
                        })
                        if debug:
                            rule_debug.append({
                                "rule": rule.get("id"),
                                "inputs": inputs,
                                "passed": res.passed,
                                "severity": res.severity,
                            })
                    except UnsafeExpression as ue:
                        # Missing/invalid variables: treat as rule failure but continue overall evaluation
                        per_rule.append({
                            "id": str(rule.get("id")),
                            "passed": False,
                            "severity": str(rule.get("severity", "info")),
                        })
                        if debug:
                            rule_debug.append({
                                "rule": rule.get("id"),
                                "inputs": inputs,
                                "error": str(ue),
                                "passed": False,
                                "severity": str(rule.get("severity", "info")),
                            })

            index = inclusivity_index(reach_ok, strength_ok, visual_ok)

            results = {
                "reach": {"ok": reach_ok, "distance_cm": distance_cm, "posture": posture},
                "strength": {
                    "ok": strength_ok,
                    "required_force_N": required_force_N,
                    "capability_N": capability_N,
                },
                "visual": {"ok": visual_ok, "contrast_ratio": contrast},
                "rules": per_rule,
            }
            if debug:
                results["debug"] = {
                    "scenario_config": cfg,
                    "rulepack_id": (run.metrics or {}).get("rulepack_id"),
                    "artifact_id": (run.metrics or {}).get("artifact_id"),
                    "fg_rgb": fg_rgb,
                    "bg_rgb": bg_rgb,
                    "contrast_ratio": contrast,
                    "rule_details": rule_debug,
                }

            run.metrics = run.metrics or {}
            run.metrics.update({
                "artifact_id": run.metrics.get("artifact_id"),
                "rulepack_id": run.metrics.get("rulepack_id"),
            })

            run.status = "done"
            run.completed_at = datetime.now(timezone.utc)
            setattr(run, "results_json", results)
            setattr(run, "inclusivity_index_json", index)
            db.add(run)
            db.commit()

            # Webhook (optional)
            webhook_url = (run.metrics or {}).get("webhook_url")
            secret = os.getenv("WEBHOOK_SECRET", "")
            if webhook_url and secret:
                try:
                    dbg("Posting webhook ...")
                    requests.post(
                        webhook_url,
                        json={
                            "id": run.id,
                            "status": run.status,
                            "results": results,
                            "index": index,
                        },
                        timeout=5,
                        headers={"X-IDP-Webhook": secret},
                    )
                except Exception as e:
                    logger.warning(f"Webhook failed: {e}")

            logger.info(f"Evaluation {evaluation_id} completed")
            return {"id": run.id, "status": run.status}
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Evaluation {evaluation_id} failed: {e}\n{tb}")
            run.status = "error"
            run.completed_at = datetime.now(timezone.utc)
            run.metrics = run.metrics or {}
            run.metrics["error"] = str(e)
            if debug:
                run.metrics["traceback"] = tb
            db.add(run)
            db.commit()
            return {"id": run.id, "status": run.status}


@celery_app.task(name="app.tasks.convert_artifact")
def convert_artifact(artifact_id: int) -> Dict[str, Any]:
    """
    Stub conversion: if artifact is STEP/STP, generate a minimal glTF placeholder and update artifact.
    """
    with SessionLocal() as db:
        art = db.get(models.DesignArtifact, artifact_id)
        if not art:
            return {"status": "not_found"}
        ext = (art.type or '').lower()
        if ext in ("gltf", "glb"):
            return {"status": "skipped", "reason": "already glTF"}
        # Generate minimal glTF JSON
        gltf = {
            "asset": {"version": "2.0", "generator": "IDP-Stub"},
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0}],
            "meshes": [{"primitives": [{"attributes": {}}]}],
        }
        key = new_object_key(art.project_id, f"artifact_{artifact_id}.gltf")
        upload_bytes(key, (str(gltf)).encode("utf-8"), "model/gltf+json")
        # Update artifact to point to new glTF
        art.object_key = key
        art.object_mime = "model/gltf+json"
        art.type = "gltf"
        db.add(art)
        db.commit()
        db.refresh(art)
        return {"status": "done", "artifact_id": artifact_id, "object_key": key}
