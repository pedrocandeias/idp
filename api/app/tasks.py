from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

import requests
from sqlalchemy.orm import Session

from .celery_app import celery_app
from .db import SessionLocal
from . import models
from .rules import evaluate_rule
from .simulations import wcag_contrast_from_rgb, reach_envelope_ok, strength_feasible, inclusivity_index


logger = logging.getLogger(__name__)


def _load_entities(db: Session, evaluation_id: int):
    run = db.get(models.EvaluationRun, evaluation_id)
    if not run:
        raise RuntimeError("EvaluationRun not found")
    scenario = db.get(models.SimulationScenario, run.scenario_id)
    rulepack = db.get(models.RulePack, run.metrics.get("rulepack_id")) if run.metrics else None
    artifact = db.get(models.DesignArtifact, run.metrics.get("artifact_id")) if run.metrics else None
    return run, scenario, rulepack, artifact


@celery_app.task(name="app.tasks.run_evaluation")
def run_evaluation(evaluation_id: int) -> Dict[str, Any]:
    logger.info(f"Starting evaluation {evaluation_id}")
    with SessionLocal() as db:
        run, scenario, rulepack, artifact = _load_entities(db, evaluation_id)
        run.status = "running"
        db.add(run)
        db.commit()

        # Simulations (very simplified, pull inputs from scenario.config or defaults)
        cfg = (scenario.config or {}) if scenario else {}
        distance_cm = float(cfg.get("distance_to_control_cm", 55.0))
        posture = str(cfg.get("posture", "seated"))
        required_force_N = float(cfg.get("required_force_N", 20.0))
        capability_N = float(cfg.get("capability_N", 25.0))
        fg_rgb = tuple(cfg.get("fg_rgb", [255, 255, 255]))
        bg_rgb = tuple(cfg.get("bg_rgb", [0, 0, 0]))

        logger.info("Sim: reach envelope check ...")
        reach_ok = reach_envelope_ok(distance_cm, posture)
        logger.info("Sim: strength feasibility ...")
        strength_ok = strength_feasible(required_force_N, capability_N)
        logger.info("Sim: visual contrast ...")
        contrast = wcag_contrast_from_rgb(fg_rgb, bg_rgb)
        visual_ok = contrast >= 4.5

        # Rules evaluation
        logger.info("Evaluating rules ...")
        per_rule = []
        if rulepack and (rulepack.rules or {}).get("rules"):
            for rule in rulepack.rules["rules"]:
                # Provide a basic variable set drawn from scenario
                inputs = {
                    "distance_cm": distance_cm,
                    "required_force_N": required_force_N,
                    "contrast_ratio": contrast,
                    # common aliases
                    "w": float(cfg.get("button_w_mm", 10)),
                    "h": float(cfg.get("button_h_mm", 10)),
                }
                res = evaluate_rule(rule, inputs)
                per_rule.append({"id": res.id, "passed": res.passed, "severity": res.severity})

        index = inclusivity_index(reach_ok, strength_ok, visual_ok)

        results = {
            "reach": {"ok": reach_ok, "distance_cm": distance_cm, "posture": posture},
            "strength": {"ok": strength_ok, "required_force_N": required_force_N, "capability_N": capability_N},
            "visual": {"ok": visual_ok, "contrast_ratio": contrast},
            "rules": per_rule,
        }

        run.metrics = (run.metrics or {})
        run.metrics.update({"artifact_id": run.metrics.get("artifact_id"), "rulepack_id": run.metrics.get("rulepack_id")})
        run_status = {"status": "done"}
        run.status = "done"
        run.completed_at = datetime.now(timezone.utc)
        # Store full JSON results
        setattr(run, "results_json", results)
        setattr(run, "inclusivity_index_json", index)
        db.add(run)
        db.commit()

        # Webhook (optional)
        webhook_url = (run.metrics or {}).get("webhook_url")
        secret = os.getenv("WEBHOOK_SECRET", "")
        if webhook_url and secret:
            try:
                logger.info("Posting webhook ...")
                requests.post(webhook_url, json={"id": run.id, "status": run.status, "results": results, "index": index}, timeout=5, headers={"X-IDP-Webhook": secret})
            except Exception as e:
                logger.warning(f"Webhook failed: {e}")

        logger.info(f"Evaluation {evaluation_id} completed")
        return {"id": run.id, "status": run.status}

