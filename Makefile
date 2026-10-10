PY := .venv/bin/python

.PHONY: dev test lint

dev:
	cd backend && ../$(PY) -m uvicorn app.main:app --reload

test:
	cd backend && ../$(PY) -m pytest

lint:
	$(PY) -m ruff check backend
