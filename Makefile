SHELL := /bin/bash

.PHONY: dev down logs ps fmt lint pre-commit-install

dev:
	docker compose up -d --build

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

fmt:
	pre-commit run --all-files --hook-stage manual || true

lint:
	pre-commit run --all-files --hook-stage manual || true

pre-commit-install:
	pre-commit install

.PHONY: demo
demo:
	# Boot services
	docker compose up -d --build
	# Give API a moment and run demo script inside api container
	docker compose exec -T api sh -lc "cd /app && python scripts/demo.py"
