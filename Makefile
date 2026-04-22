.PHONY: install up down logs dev worker test lint format migrate revision tailwind new-module bootstrap-local bootstrap-localstack seed clean

UV := uv

install:
	$(UV) sync --all-packages

bootstrap-local: install up
	@echo "Waiting for Postgres & LocalStack to be ready..."
	@sleep 5
	$(MAKE) migrate
	$(MAKE) bootstrap-localstack
	@echo ""
	@echo "Done. Start dev server with: make dev (in 1 shell) + make worker (in another)"

bootstrap-localstack:
	./scripts/bootstrap_localstack.sh

seed:
	$(UV) run python scripts/seed.py

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

dev:
	cd apps/web && $(UV) run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	cd apps/judge-worker && $(UV) run python -m worker.main

migrate:
	cd apps/web && $(UV) run alembic upgrade head

revision:
	@test -n "$(m)" || (echo "Usage: make revision m=\"message\"" && exit 1)
	cd apps/web && $(UV) run alembic revision --autogenerate -m "$(m)"

tailwind:
	cd apps/web && tailwindcss -i static/css/input.css -o static/css/app.css --watch

lint:
	$(UV) run ruff check .
	$(UV) run mypy apps/web/app apps/judge-worker/worker

format:
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

test:
	$(UV) run pytest

new-module:
	@test -n "$(name)" || (echo "Usage: make new-module name=xxx" && exit 1)
	$(UV) run python scripts/new_module.py $(name)

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .mypy_cache .ruff_cache .pytest_cache .coverage htmlcov
