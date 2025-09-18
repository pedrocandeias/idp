from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests
import typer
from platformdirs import user_config_dir


app = typer.Typer(help="IDP CLI")
eval_app = typer.Typer(help="Evaluation commands")
report_app = typer.Typer(help="Report commands")
datasets_app = typer.Typer(help="Datasets commands")
app.add_typer(eval_app, name="eval")
app.add_typer(report_app, name="report")
app.add_typer(datasets_app, name="datasets")


CONF_DIR = Path(user_config_dir("idp-cli", "idp"))
CONF_FILE = CONF_DIR / "config.json"


def load_config() -> dict:
    cfg = {"base_url": os.getenv("IDP_API_URL", "http://localhost:8000"), "token": os.getenv("IDP_TOKEN")}
    if CONF_FILE.exists():
        try:
            cfg.update(json.loads(CONF_FILE.read_text()))
        except Exception:
            pass
    return cfg


def save_config(cfg: dict) -> None:
    CONF_DIR.mkdir(parents=True, exist_ok=True)
    CONF_FILE.write_text(json.dumps(cfg, indent=2))


def _headers(token: Optional[str]) -> dict:
    h = {"Accept": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


@app.command()
def login(
    base_url: str = typer.Option("http://localhost:8000", help="API base URL"),
    token: str = typer.Option(..., prompt=True, hide_input=True, help="JWT access token"),
    json_out: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Save API URL and token to local user config."""
    cfg = load_config()
    cfg.update({"base_url": base_url, "token": token})
    save_config(cfg)
    if json_out:
        typer.echo(json.dumps({"ok": True, "config": {"base_url": base_url}}))
    else:
        typer.echo(f"Saved config for {base_url}")


@eval_app.command("submit")
def eval_submit(
    artifact: int = typer.Option(..., "--artifact", help="Artifact ID"),
    scenario: int = typer.Option(..., "--scenario", help="Scenario ID"),
    rulepack: int = typer.Option(..., "--rulepack", help="RulePack ID"),
    json_out: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Submit an evaluation run."""
    cfg = load_config()
    url = f"{cfg['base_url'].rstrip('/')}/api/v1/evaluations"
    try:
        r = requests.post(url, json={"artifact_id": artifact, "scenario_id": scenario, "rulepack_id": rulepack}, headers=_headers(cfg.get("token")), timeout=30)
        if not r.ok:
            typer.echo(r.text, err=True)
            raise SystemExit(1)
        data = r.json()
        if json_out:
            typer.echo(json.dumps(data))
        else:
            typer.echo(f"Run ID: {data['id']} Status: {data['status']}")
    except Exception as e:
        typer.echo(str(e), err=True)
        raise SystemExit(1)


@eval_app.command("wait")
def eval_wait(
    id: int = typer.Option(..., "--id", help="Evaluation run ID"),
    interval: float = typer.Option(2.0, help="Polling interval seconds"),
    json_out: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Wait for an evaluation to finish and print final status."""
    cfg = load_config()
    url = f"{cfg['base_url'].rstrip('/')}/api/v1/evaluations/{id}"
    try:
        while True:
            r = requests.get(url, headers=_headers(cfg.get("token")), timeout=30)
            if not r.ok:
                typer.echo(r.text, err=True)
                raise SystemExit(1)
            data = r.json()
            status = data.get("status")
            if status in ("done", "failed", "error"):
                if json_out:
                    typer.echo(json.dumps(data))
                else:
                    typer.echo(f"Status: {status}")
                raise SystemExit(0 if status == "done" else 2)
            time.sleep(interval)
    except SystemExit:
        raise
    except Exception as e:
        typer.echo(str(e), err=True)
        raise SystemExit(1)


@report_app.command("fetch")
def report_fetch(
    id: int = typer.Option(..., "--id", help="Evaluation run ID"),
    out: Path = typer.Option(Path("reports"), "--out", help="Output directory"),
    json_out: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Generate and download HTML/PDF report for a run."""
    cfg = load_config()
    base = cfg['base_url'].rstrip('/')
    try:
        # trigger report build
        r = requests.post(f"{base}/api/v1/evaluations/{id}/report", headers=_headers(cfg.get("token")), timeout=60)
        if not r.ok:
            typer.echo(r.text, err=True)
            raise SystemExit(1)
        rep = r.json()
        out.mkdir(parents=True, exist_ok=True)
        html_path = out / f"run_{id}.html"
        pdf_path = out / f"run_{id}.pdf"
        # download
        h = requests.get(rep["presigned_html_url"], timeout=60)
        h.raise_for_status()
        html_path.write_bytes(h.content)
        p = requests.get(rep["presigned_pdf_url"], timeout=60)
        p.raise_for_status()
        pdf_path.write_bytes(p.content)
        result = {"html": str(html_path), "pdf": str(pdf_path), "checksum": rep.get("checksum_sha256")}
        if json_out:
            typer.echo(json.dumps(result))
        else:
            typer.echo(f"Saved {html_path} and {pdf_path}")
    except SystemExit:
        raise
    except Exception as e:
        typer.echo(str(e), err=True)
        raise SystemExit(1)


@datasets_app.command("list")
def datasets_list(json_out: bool = typer.Option(False, "--json", help="JSON output")):
    """List available datasets (anthropometrics and abilities)."""
    cfg = load_config()
    base = cfg['base_url'].rstrip('/')
    try:
        r1 = requests.get(f"{base}/api/v1/datasets/anthropometrics", headers=_headers(cfg.get("token")), timeout=30)
        r2 = requests.get(f"{base}/api/v1/datasets/abilities", headers=_headers(cfg.get("token")), timeout=30)
        if not r1.ok or not r2.ok:
            typer.echo(f"{r1.status_code}:{r1.text} {r2.status_code}:{r2.text}", err=True)
            raise SystemExit(1)
        data = {"anthropometrics": r1.json(), "abilities": r2.json()}
        if json_out:
            typer.echo(json.dumps(data))
        else:
            typer.echo(f"Anthropometrics: {len(data['anthropometrics'])} • Abilities: {len(data['abilities'])}")
    except SystemExit:
        raise
    except Exception as e:
        typer.echo(str(e), err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    app()

