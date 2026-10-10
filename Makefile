# Spin Count (Vinyl Second-Brain). One Python 3.11 env (.venv) and one Node env (.nodeenv).
PY := .venv/bin/python
export PATH := $(CURDIR)/.nodeenv/bin:$(PATH)
PORT ?= 8000

.PHONY: help setup run dev frontend-dev build test test-frontend e2e test-all lint coverage \
        sync-vault openapi types backup

help:
	@echo "make run        build the app and serve it on http://127.0.0.1:$(PORT)  (sets everything up first)"
	@echo "make dev        API with auto-reload; run 'make frontend-dev' in a second terminal"
	@echo "make test-all   backend tests, frontend tests and the browser tests"
	@echo "make backup     copy the database to backend/backups/ now"

# ---- environments (created on first use) ----
$(PY):
	/opt/anaconda3/bin/python3.11 -m venv .venv || python3.11 -m venv .venv
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -r requirements.lock.txt

.nodeenv/bin/node:
	@command -v conda >/dev/null || [ -x /opt/anaconda3/bin/conda ] || { echo "Node 22 is needed: install it, or install conda."; exit 1; }
	$$(command -v conda || echo /opt/anaconda3/bin/conda) create -y -q -p ./.nodeenv -c conda-forge --override-channels nodejs=22

frontend/node_modules: frontend/package-lock.json .nodeenv/bin/node
	cd frontend && npm ci --silent
	@touch frontend/node_modules

setup: $(PY) frontend/node_modules
	@[ -f .env ] || { cp .env.example .env; echo "Created .env: add your DISCOGS_TOKEN."; }

# ---- run ----
build: frontend/node_modules
	cd frontend && npm run --silent build

run: setup build
	cd backend && PYTHONPATH=..:. ../$(PY) -m uvicorn app.main:app --host 127.0.0.1 --port $(PORT)

dev: $(PY)
	cd backend && PYTHONPATH=..:. ../$(PY) -m uvicorn app.main:app --reload --port $(PORT)

frontend-dev: frontend/node_modules
	cd frontend && BACKEND_URL=http://127.0.0.1:$(PORT) npm run dev

# ---- checks ----
test: $(PY)
	cd backend && ../$(PY) -m pytest

test-frontend: frontend/node_modules
	cd frontend && npm run --silent test

e2e: frontend/node_modules
	cd frontend && npx playwright install chromium >/dev/null && npm run --silent e2e

test-all: test test-frontend e2e

lint: $(PY)
	$(PY) -m ruff check backend

coverage: $(PY)
	cd backend && ../$(PY) -m pytest --cov=app --cov-report=term-missing:skip-covered -q

# ---- tools ----
sync-vault: $(PY)
	cd backend && PYTHONPATH=..:. ../$(PY) -m app.vault

openapi: $(PY)
	cd backend && PYTHONPATH=..:. ../$(PY) -m app.export_openapi

types: openapi frontend/node_modules
	cd frontend && npm run --silent api:types

backup: $(PY)
	cd backend && PYTHONPATH=..:. ../$(PY) -m app.backup
