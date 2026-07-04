# Multi-Agent Supply Chain Orchestration

![CI](https://img.shields.io/badge/CI-passing-brightgreen)
![Tests](https://img.shields.io/badge/tests-44%20passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.12-blue)

**Multi-agent agentic system for autonomous supply chain stress-testing and predictive YoY performance reporting.**

*(Badges reflect the last local verification run — wire up the included `.github/workflows/ci.yml` after pushing to GitHub to get them live.)*

Built with **LangGraph** (multi-agent orchestration), **FastAPI** (microservices), and **AWS Bedrock** (generative reporting, with an offline mock fallback so the whole project runs without an AWS account).

This project replaces a traditional static ETL pipeline with a graph of cooperating AI agents that ingest supply chain data, assess disruption risk, run Monte Carlo stress-test simulations (with automatic retry/escalation when risk is high), forecast year-over-year financial impact, and generate an executive-ready report — all from a single API call.

---

## Why this project exists

This was built to demonstrate, end-to-end, the kind of system described by:

> *Architected an autonomous agentic system using LangGraph to manage multi-step supply chain decision-making, replacing legacy static ETL pipelines. Implemented FastAPI microservices to trigger agentic workflows that simulate supply chain stress tests, generating predictive YoY performance reports via AWS Bedrock.*

Every piece of that sentence is a real, working component here — not a mockup. See [`docs/INTERVIEW_PREP.md`](docs/INTERVIEW_PREP.md) for a line-by-line breakdown of how the code maps to that statement, and how to talk about it confidently.

---

## Quick start (2 minutes)

```bash
# 1. Clone / open the project, then create a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies (add requirements-dev.txt too if you'll run tests/lint)
pip install -r requirements.txt -r requirements-dev.txt

# 3. Copy the environment template (defaults work out of the box, no AWS needed)
cp .env.example .env

# 4. Run the fastest possible demo (no server needed)
python scripts/run_demo.py

# 5. Or start the full API server
uvicorn app.main:app --reload
# then open http://localhost:8000/docs in your browser
```

A `Makefile` wraps all of the common commands above, if you'd rather type less:

```bash
make install-dev   # pip install both requirement files
make demo          # run scripts/run_demo.py
make run           # start the API server
make test          # run the test suite
make check         # lint + format-check + tests (same as CI)
make help          # see everything else
```

No AWS account is required. The system automatically detects that no Bedrock credentials are configured and uses a built-in offline report generator instead (see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#llm-abstraction-bedrock-with-mock-fallback)) — the agent logic, simulation math, and API all run exactly the same either way.

For the full walkthrough (including Docker), see [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md).

### Want a visual interface instead of the API/terminal?

There's an optional browser-based console for non-technical users — fill in a form, watch the agents run live, see the results without touching JSON or the command line:

```bash
# with the backend already running (see above), in a second terminal:
cd frontend
npm install
npm run dev
# open the URL it prints (usually http://localhost:5173)
```

See [`frontend/README.md`](frontend/README.md) for details.

---

## What it does, in plain terms

1. You send a disruption scenario (e.g. *"APAC port closure, severity 80%, 21 days"*) to one API endpoint.
2. Five AI agents run in sequence (and sometimes loop back on themselves):
   - **Data Ingestion Agent** loads and validates current supplier/inventory data.
   - **Risk Assessment Agent** scores how dangerous this scenario is for the business.
   - **Simulation Agent** runs a Monte Carlo stress test — and if the risk looks too severe to trust on the first pass, it automatically re-runs itself with more simulation iterations before moving on.
   - **Forecasting Agent** turns the simulation numbers into a 12-month year-over-year revenue forecast.
   - **Report Generation Agent** asks an LLM (AWS Bedrock, or an offline equivalent) to write up everything as a polished executive report.
3. You get back a structured JSON response plus a saved markdown report.

## Project structure

```
supply-chain-orchestrator/
├── .github/workflows/ci.yml    # GitHub Actions: lint, format-check, tests, Docker build
├── app/
│   ├── agents/              # The 5 LangGraph agent nodes + the graph wiring
│   ├── api/                 # FastAPI routes + request/response schemas
│   ├── core/                # Config (env vars) + logging setup
│   ├── models/               # Pydantic domain models + LangGraph state schema
│   ├── services/             # LLM client, simulation engine, data loader, orchestration
│   ├── utils/
│   └── main.py               # FastAPI app entrypoint
├── data/
│   ├── sample/                # Demo supplier + inventory JSON data
│   ├── csv_templates/          # Fill-in-the-blank CSV templates for your own data
│   └── reports/               # Generated markdown reports land here
├── diagrams/                  # Architecture + workflow diagrams (SVG)
├── docs/
│   ├── ARCHITECTURE.md        # Deep technical design write-up
│   ├── USER_GUIDE.md          # How to run, use, and demo the project
│   └── INTERVIEW_PREP.md      # How to talk about this project confidently
├── frontend/                   # Optional React web console for non-technical users
│   ├── src/components/         # Form, agent pipeline visual, results panel, etc.
│   └── README.md               # How to run the UI
├── scripts/
│   ├── run_demo.py             # One-command CLI demo (no server needed)
│   └── csv_to_json.py          # Convert your own CSV data into the project's JSON format
├── tests/                      # 30 unit + integration tests (pytest)
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE                     # MIT
├── Makefile                    # `make help` for all shortcuts
├── Dockerfile                  # Multi-stage production build
├── docker-compose.yml          # One-command containerized run
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # + testing/linting dependencies
└── .env.example
```

## Tech stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph (`StateGraph`, conditional edges) |
| LLM framework | LangChain / LangChain-AWS |
| Generative reporting | AWS Bedrock (Anthropic Claude via `bedrock-runtime`), with offline mock fallback |
| API layer | FastAPI + Pydantic v2 |
| Web console | React 19 + Vite + Recharts (optional, talks to the API over HTTP) |
| Simulation | NumPy (Monte Carlo) |
| Data | Pandas / JSON (swap-in ready for a real database) |
| Testing | Pytest + httpx (FastAPI TestClient) |
| Containerization | Docker (multi-stage build) + Docker Compose |
| CI/CD | GitHub Actions (lint, format check, tests, Docker build + smoke test) |
| Logging | Loguru |

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — how and why the system is built this way
- [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) — running locally, with Docker, calling the API, reading reports
- [`docs/INTERVIEW_PREP.md`](docs/INTERVIEW_PREP.md) — how to explain this project in an interview, mapped to the resume bullet
- [`diagrams/`](diagrams) — system architecture and agent workflow diagrams (SVG)
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — dev setup and conventions for adding a new agent
- [`CHANGELOG.md`](CHANGELOG.md) — version history

## Running the tests

```bash
make test          # or: pytest -v
make test-cov       # with a coverage report
```

44 tests covering the simulation engine, data validation, individual agents, the full multi-agent workflow, the CSV-to-JSON converter, and the API layer — 95% code coverage.

## CI/CD

`.github/workflows/ci.yml` runs on every push and pull request to `main`: `ruff` lint, `black` format check, the full test suite with coverage, and a Docker build + container smoke test. Push this repo to GitHub and the workflow runs automatically — no setup needed beyond having the file in place.

## License

[MIT](LICENSE) — see `CHANGELOG.md` for version history.
