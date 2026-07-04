# Changelog

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) conventions and [Semantic Versioning](https://semver.org/).

## [1.2.0] - 2026-06-23

### Added
- `frontend/` — a React (Vite) web console for non-technical users: a form to run stress tests, a live "agent manifest" visual showing each agent stamping through the pipeline (with retry/escalation visible as a distinct tag), a results panel with a forecast chart, and drag-and-drop-style CSV upload for suppliers/inventory data.
- New backend endpoints to support the UI: `GET /api/v1/data/summary` (current supplier/inventory counts and regions) and `POST /api/v1/data/upload` (upload a CSV to replace the live data, reusing the same validation as `scripts/csv_to_json.py`).
- `app/services/csv_converter_service.py` — the CSV validation/conversion logic was moved here from the CLI script so both the script and the new upload endpoint share one implementation. `scripts/csv_to_json.py` is now a thin wrapper around it.
- `sample_data_dir` setting (`app/core/config.py`) so the data directory is configurable rather than hardcoded, enabling safe test isolation for the new upload endpoint.
- 4 new API tests for the upload/summary endpoints, with proper test isolation (uploads in tests are redirected to a temp directory via `monkeypatch`, never touching the real demo data). Total test count: 44, coverage: 95%.

## [1.1.0] - 2026-06-22

### Added
- `scripts/csv_to_json.py` — converts a suppliers or inventory CSV file into the project's JSON format, with schema validation that reports the exact row/column of any problem (missing columns, non-numeric values) instead of failing silently.
- `data/csv_templates/` — fill-in-the-blank CSV templates for suppliers and inventory, plus a plain-language column guide (`data/csv_templates/README.md`).
- `make csv-suppliers CSV=path.csv` and `make csv-inventory CSV=path.csv` Makefile shortcuts.
- 7 new tests covering the converter (valid conversion, missing columns, invalid numbers, multi-row files, Excel-style float-looking integers). Total test count: 37, coverage: 95%.
- `docs/USER_GUIDE.md` section explaining how to swap in your own data.

## [1.0.0] - 2026-06-21

### Added
- Initial release of SupplyChain Sentinel.
- Five-agent LangGraph workflow: Data Ingestion, Risk Assessment, Simulation, Forecasting, Report Generation.
- Conditional retry/escalation loop in the Simulation agent — re-runs Monte Carlo simulation with increased iteration count when computed risk is high and stockout probability exceeds 50%.
- Monte Carlo stress-test simulation engine (`app/services/simulation_engine.py`) with reproducible seeding.
- AWS Bedrock integration for report generation, with an automatic offline mock LLM fallback when no AWS credentials are configured (`app/services/llm_service.py`).
- FastAPI microservice layer with `/stress-test`, `/reports`, `/reports/{slug}`, and `/health` endpoints.
- Sample supply chain dataset (6 suppliers, 8 SKUs) under `data/sample/`.
- Full test suite: 30 tests across unit (simulation engine, data loader, individual agents), integration (full graph workflow), and API layers. 94% code coverage.
- Docker support: multi-stage `Dockerfile` (non-root user, healthcheck) and `docker-compose.yml`.
- GitHub Actions CI pipeline: lint (ruff), format check (black), test suite with coverage, and a Docker build + smoke test.
- CLI demo script (`scripts/run_demo.py`) for running a scenario without starting the API server.
- Full documentation suite: `README.md`, `docs/ARCHITECTURE.md`, `docs/USER_GUIDE.md`, `docs/INTERVIEW_PREP.md`.
- Architecture and workflow diagrams (`diagrams/*.svg`).

### Design notes
- Risk scoring is deterministic/rule-based rather than LLM-driven, by design, for explainability and reproducibility.
- YoY forecasting uses a transparent formula-driven model rather than a trained time-series model, as an explicit v1 scope decision (see `docs/ARCHITECTURE.md` for the v2 path).
