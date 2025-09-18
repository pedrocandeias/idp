#!/usr/bin/env python
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

from app.db import SessionLocal
from app import models


BASE = os.getenv("DEMO_BASE_URL", "http://localhost:8000")
EMAIL = os.getenv("DEMO_EMAIL", "demo@idp.local")
PASSWORD = os.getenv("DEMO_PASSWORD", "demo123")


def api(method: str, path: str, token: str | None = None, **kwargs):
    url = f"{BASE}{path}"
    headers = kwargs.pop("headers", {})
    headers.setdefault("Accept", "application/json")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.request(method, url, headers=headers, timeout=30, **kwargs)
    return resp


def wait_api():
    for _ in range(60):
        try:
            r = requests.get(f"{BASE}/api/v1/health", timeout=5)
            if r.ok:
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("API not responding")


def main():
    wait_api()

    # Register/login
    api("POST", "/auth/register", json={"email": EMAIL, "password": PASSWORD}).raise_for_status()
    r = requests.post(f"{BASE}/auth/token", data={"username": EMAIL, "password": PASSWORD}, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    r.raise_for_status()
    token = r.json()["access_token"]

    # Create rulepack (if not exists)
    with open(Path(__file__).resolve().parent.parent / "seeds" / "rulepack_general_eu_v1.json", "r") as f:
        rp_payload = json.load(f)
    lst = api("GET", "/api/v1/rulepacks", token).json()
    rp = next((x for x in lst if x.get("name") == rp_payload["name"]), None)
    if not rp:
        rp = api("POST", "/api/v1/rulepacks", token, json=rp_payload).json()

    # Create project
    proj = api("POST", "/api/v1/projects", token, json={"name": "Demo Project", "description": "Demo"}).json()

    # Create scenario directly in DB
    with SessionLocal() as db:
        sc = models.SimulationScenario(project_id=proj["id"], name="Demo Scenario", config={
            "distance_to_control_cm": 50,
            "fg_rgb": [255, 255, 255],
            "bg_rgb": [0, 0, 0],
            "required_force_N": 15,
            "capability_N": 20,
        })
        db.add(sc)
        db.commit()
        db.refresh(sc)
        scenario_id = sc.id

    # Upload artifact
    gltf_path = Path(__file__).resolve().parent.parent / "seeds" / "minimal.gltf"
    files = {
        "file": ("minimal.gltf", gltf_path.read_bytes(), "model/gltf+json"),
        "params": ("params.json", json.dumps({"demo": True}).encode("utf-8"), "application/json"),
    }
    up = requests.post(f"{BASE}/api/v1/projects/{proj['id']}/artifacts", files=files, headers={"Authorization": f"Bearer {token}"}, timeout=60)
    up.raise_for_status()
    art = up.json()

    # Enqueue evaluation
    enq = api("POST", "/api/v1/evaluations", token, json={"artifact_id": art["id"], "scenario_id": scenario_id, "rulepack_id": rp["id"]}).json()
    run_id = enq["id"]

    # Wait for completion
    while True:
        st = api("GET", f"/api/v1/evaluations/{run_id}", token).json()
        if st.get("status") == "done":
            break
        time.sleep(1)

    # Generate report
    rep = api("POST", f"/api/v1/evaluations/{run_id}/report", token).json()
    print(rep.get("presigned_pdf_url"))


if __name__ == "__main__":
    main()

