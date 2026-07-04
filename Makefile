# Makefile
# ---------
# Convenience shortcuts for the most common commands. Run `make help` to see
# all of them. None of these are required -- everything here is just the
# plain command underneath, wrapped in a short name so you don't have to
# remember the exact flags every time.

.PHONY: help install install-dev run demo csv-suppliers csv-inventory test test-cov lint format check docker-build docker-up docker-down clean

help:
	@echo "Available commands:"
	@echo "  make install       Install production dependencies"
	@echo "  make install-dev   Install production + dev/test dependencies"
	@echo "  make run           Start the FastAPI server (with auto-reload)"
	@echo "  make demo          Run the one-shot CLI demo script"
	@echo "  make csv-suppliers CSV=path/to/file.csv   Convert a suppliers CSV into data/sample/suppliers.json"
	@echo "  make csv-inventory CSV=path/to/file.csv   Convert an inventory CSV into data/sample/inventory.json"
	@echo "  make test          Run the test suite"
	@echo "  make test-cov      Run the test suite with a coverage report"
	@echo "  make lint          Check code style with ruff"
	@echo "  make format        Auto-format code with black"
	@echo "  make check         Run lint + format-check + tests (what CI runs)"
	@echo "  make docker-build  Build the Docker image"
	@echo "  make docker-up     Build and start the app with docker compose"
	@echo "  make docker-down   Stop the docker compose stack"
	@echo "  make clean         Remove caches, __pycache__, and generated reports"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

demo:
	python scripts/run_demo.py

csv-suppliers:
	python scripts/csv_to_json.py suppliers $(CSV)

csv-inventory:
	python scripts/csv_to_json.py inventory $(CSV)

test:
	pytest -v

test-cov:
	pytest -v --cov=app --cov-report=term-missing

lint:
	ruff check app/ tests/ scripts/

format:
	black app/ tests/ scripts/

check: lint
	black --check app/ tests/ scripts/
	pytest -v

docker-build:
	docker build -t supply-chain-sentinel:latest .

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -not -path "./venv/*" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
	rm -f data/reports/*.md data/reports/*.log
