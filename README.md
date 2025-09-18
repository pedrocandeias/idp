# Inclusive Design Platform (idp)

Monorepo scaffold for the Inclusive Design Platform. This initial commit provides dev tooling only — services are placeholders with no framework logic yet.

## Services

- api (Python placeholder)
- worker (Python placeholder)
- web (Node placeholder)
- postgres
- redis
- minio
- docs

Service names match `docker-compose.yml`.

## Quickstart

1. Prerequisites
   - Docker and Docker Compose
   - Make
   - Python 3.11+ (for local pre-commit)

2. Setup environment
   - Copy env file: `cp .env.example .env`

3. Start dev stack
   - `make dev`
   - This builds and starts the containers: `api`, `worker`, `web`, `postgres`, `redis`, `minio`, `docs`.

4. Inspect
   - `make ps` to see status
   - `make logs` for aggregated logs
   - `make down` to stop and remove containers/volumes

## Tooling

- Pre-commit: Black, isort, Ruff (Python); Prettier + ESLint (web)
- CI: GitHub Actions runs pre-commit on push/PR

Install hooks locally:

```bash
pip install pre-commit
make pre-commit-install
```

Run format/lint locally:

```bash
make fmt
make lint
```

## Repo Layout

```
api/            # Python API placeholder
worker/         # Python worker placeholder
web/            # Web placeholder (Node)
docs/           # Docs placeholder
.github/        # CI
```

## License

MIT

