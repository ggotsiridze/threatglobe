# ThreatGlobe — common tasks. Run `make help` for the list.
SHELL := /bin/bash
PY ?= python3.12
VENV := backend/.venv
FRONTEND_URL ?= http://localhost:8080

.DEFAULT_GOAL := help
.PHONY: help demo down logs install dev test test-backend test-frontend lint build verify e2e data clean

help: ## Show this help
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

demo: ## Build and start the full demo stack in Docker (http://localhost:8080)
	docker compose up --build -d
	@echo "Waiting for services to become healthy..."
	@for i in $$(seq 1 90); do \
	  [ "$$(docker compose ps --format '{{.Health}}' | grep -c healthy)" = 2 ] && break; sleep 1; done
	@docker compose ps
	@echo
	@echo "  ThreatGlobe (DEMO MODE) → $(FRONTEND_URL)"
	@echo "  API docs               → http://localhost:8000/docs"
	@echo "  Smoke test             → make verify"

down: ## Stop the Docker stack
	docker compose down

logs: ## Follow Docker logs
	docker compose logs -f

install: ## Install local dev dependencies (Python 3.12 venv + npm ci)
	$(PY) -m venv $(VENV)
	$(VENV)/bin/pip install -q -r backend/requirements-dev.txt
	cd frontend && npm ci

dev: ## Run backend (:8000, autoreload) and Vite dev server (:5173) without Docker
	@trap 'kill 0' EXIT; \
	(cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000) & \
	(cd frontend && npm run dev) & \
	wait

test: test-backend test-frontend ## Run all unit/integration tests

test-backend: ## pytest
	cd backend && .venv/bin/python -m pytest

test-frontend: ## vitest
	cd frontend && npm test

lint: ## ruff + TypeScript typecheck
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd frontend && npm run typecheck

build: ## Production frontend build
	cd frontend && npm run build

verify: ## Smoke-test a running stack (REST, WebSocket, privacy, headers)
	FRONTEND_URL=$(FRONTEND_URL) scripts/verify.sh

e2e: ## verify + Playwright browser tests against a running stack
	FRONTEND_URL=$(FRONTEND_URL) scripts/verify.sh --e2e

data: ## Regenerate the sanitized demo dataset (deterministic)
	$(PY) scripts/generate_demo_data.py

clean: ## Remove build outputs and caches
	rm -rf frontend/dist frontend/test-results backend/.pytest_cache backend/.ruff_cache
