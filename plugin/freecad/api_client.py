from __future__ import annotations

import json
import os
from typing import Optional

import requests


class ApiClient:
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.token = token

    def _headers(self) -> dict:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def upload_artifact(self, project_id: int, step_path: str, params: dict, name: Optional[str] = None) -> dict:
        url = f"{self.base_url}/api/v1/projects/{project_id}/artifacts"
        files = {
            "file": (os.path.basename(step_path), open(step_path, "rb"), "application/step"),
            "params": ("params.json", json.dumps(params).encode("utf-8"), "application/json"),
        }
        data = {}
        if name:
            data["name"] = name
        resp = requests.post(url, headers=self._headers(), files=files, data=data, timeout=60)
        if not resp.ok:
            raise RuntimeError(f"Upload failed: {resp.status_code} {resp.text}")
        return resp.json()

