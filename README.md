# Inclusive Design Platform (IDP)

[![CI](https://github.com/ORG/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/ORG/REPO/actions/workflows/ci.yml)

> Replace `ORG/REPO` above with your GitHub org/repo to activate the badge link.

Monorepo for IDP. It includes a FastAPI backend with JWT auth, Postgres, Redis, MinIO, Celery worker, a React/Vite web UI, a Python Typer CLI, a FreeCAD add‑on, seeds + a one‑shot demo script, and GitHub Actions CI.

## Contents
- Quick Start (Docker Compose)
- End‑to‑End Demo (one command)
- Manual Flow (login → project → upload → evaluate → report)
- Web App Usage
- CLI Usage
- FreeCAD Add‑on
- Development (lint, tests, types)
- CI on GitHub
- Troubleshooting

## Quick Start (Docker Compose)

1) Prerequisites
- Docker and Docker Compose
- Make
- (Optional) Python 3.11+ if you want to run tests locally

2) Configure environment
- `cp .env.example .env`
- Keep defaults for local dev. Ensure ports 8000 (API) and 3000 (web) are free.

3) Start the dev stack
- `make dev`
- Services started: `api`, `worker`, `web`, `postgres`, `redis`, `minio`.

4) Verify
- API health: `curl http://localhost:8000/api/v1/health` → `{ "status": "ok" }`
- Web UI: http://localhost:3000

Common commands
- `make ps` — show containers
- `make logs` — tail all logs
- `make down` — stop and remove containers/volumes

## End‑to‑End Demo (one command)
Runs migrations, seeds, registers a demo user, uploads a tiny glTF, enqueues an evaluation, waits for completion, generates a report, and prints a presigned PDF URL.

- `make demo`

Output
- The last line is a presigned link (valid temporarily) to the generated PDF report in MinIO. Paste it into a browser to view.

Demo credentials for the web app
- email: `demo@idp.local`
- password: `demo123`

## Manual Flow (API)
If you want to drive the flow yourself with curl.

1) Register and login
```bash
# Register (will auto‑create a default org if needed)
curl -sX POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"secret"}'
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=you@example.com&password=secret' | jq -r .access_token)
AUTH="Authorization: Bearer $TOKEN"
```

2) Create a project
```bash
curl -sX POST http://localhost:8000/api/v1/projects \
  -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"My Project"}' | tee /tmp/proj.json
PROJ_ID=$(jq -r .id /tmp/proj.json)
```

3) Upload an artifact (glTF + optional param JSON)
```bash
curl -sX POST http://localhost:8000/api/v1/projects/$PROJ_ID/artifacts \
  -H "$AUTH" \
  -F file=@api/seeds/minimal.gltf \
  -F params=@<(echo '{"demo":true}') | tee /tmp/art.json
ART_ID=$(jq -r .id /tmp/art.json)
```

4) Create a scenario and rulepack
- The demo creates a simple scenario in the DB (see `api/scripts/demo.py`). For manual API only, you can insert a scenario directly via DB or add an endpoint later.
- Use the seeded “General EU v1” rulepack or create your own via `/api/v1/rulepacks`.

5) Enqueue evaluation
```bash
RUN=$(curl -sX POST http://localhost:8000/api/v1/evaluations \
  -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"artifact_id":'"$ART_ID"',"scenario_id":1,"rulepack_id":1}')
RUN_ID=$(echo "$RUN" | jq -r .id)
```

6) Poll for completion
```bash
curl -s http://localhost:8000/api/v1/evaluations/$RUN_ID -H "$AUTH" | jq .
```

7) Generate report and open link
```bash
curl -sX POST http://localhost:8000/api/v1/evaluations/$RUN_ID/report -H "$AUTH" | jq .
```

Tip: Use the CLI below to submit/wait/fetch easily.

## Web App Usage
- Go to http://localhost:3000
- Log in (demo credentials above or your own).
- Projects page: create a project; open a project.
- Artifacts page: `#/projects/:id/artifacts` — drag & drop glTF/GLB/STEP and optional params JSON, then enqueue an evaluation (enter scenario + rulepack IDs).
- Evaluation page: `#/evaluations/:id` — 3D viewer (glTF), toggle reach envelope, see per‑rule breakdown and Inclusivity Index. “Recompute” enqueues a new run.

Accessibility
- Viewer supports keyboard focus; controls are labeled; ARIA attributes added on key widgets.

## CLI Usage (Typer)
Run locally or inside the api container.

Configure
```bash
python -m api.cli.idp login --base-url http://localhost:8000
# You’ll be prompted for the JWT token (from /auth/token)
```

Submit, wait, and fetch report
```bash
python -m api.cli.idp eval submit --artifact 1 --scenario 1 --rulepack 1 --json | jq .
python -m api.cli.idp eval wait --id 123
python -m api.cli.idp report fetch --id 123 --out reports/
```

Datasets
```bash
python -m api.cli.idp datasets list --json | jq .
```

Tokens are stored in your user config dir (created if missing):
- Linux: `~/.config/idp-cli/config.json`
- macOS: `~/Library/Application Support/idp-cli/config.json`
- Windows: `%APPDATA%\idp-cli\config.json`

## FreeCAD Add‑on
Path: `plugin/freecad`

Install
- Copy `plugin/freecad` to your FreeCAD `Mod/` folder:
  - Linux: `~/.local/share/FreeCAD/Mod/idp_freecad`
  - macOS: `~/Library/Preferences/FreeCAD/Mod/idp_freecad`
  - Windows: `%APPDATA%/FreeCAD/Mod/idp_freecad`
- Restart FreeCAD → Tools → IDP → Export & Upload.

Use
- Set API URL and JWT token; enter a Project ID; click “Export & Upload”.
- The add‑on exports STEP from the active document and uploads parametric JSON metadata.

Tests
- `python -m pytest plugin/freecad/tests -q`

## Development

Lint/format
```bash
pip install pre-commit
make pre-commit-install
make fmt
make lint
```

Tests & types (API)
```bash
cd api
pip install -r requirements.txt
pytest -q
mypy app || true
```

## CI on GitHub
- Workflow: `.github/workflows/ci.yml`
- Runs: pre-commit, mypy, pytest, and builds Docker images.
- Enable Actions in your repo; update the README badge to your `ORG/REPO`.

## Troubleshooting
- Entry script permission error on api: compose runs with `sh /app/entrypoint.sh` to avoid exec bit issues.
- Migrations failing: `make logs` (api service) and ensure Postgres is up; rerun `make dev`.
- Presigned URLs expire: re‑POST `/evaluations/{id}/report`.
- MinIO console: http://localhost:9001 (default creds in `.env.example`).
- Worker must be running for evaluations to complete.

## Repository Layout
```
api/            # FastAPI app, Alembic, Celery tasks, CLI
web/            # React + Vite web app
plugin/freecad/ # FreeCAD add-on (PySide UI)
docs/           # SECURITY.md and future docs
.github/        # CI
```

## License
MIT

