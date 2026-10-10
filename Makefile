PY := .venv/bin/python

.PHONY: dev test lint coverage sync-vault openapi backup

dev:
	cd backend && PYTHONPATH=..:. ../$(PY) -m uvicorn app.main:app --reload

test:
	cd backend && ../$(PY) -m pytest

lint:
	$(PY) -m ruff check backend

sync-vault:
	cd backend && PYTHONPATH=..:. ../$(PY) -m app.vault

coverage:
	cd backend && ../$(PY) -m pytest --cov=app --cov-report=term-missing:skip-covered -q

openapi:
	cd backend && PYTHONPATH=..:. ../$(PY) -m app.export_openapi

backup:
	cd backend && PYTHONPATH=..:. ../$(PY) -m app.backup
