# Contributing

This started as a portfolio/demo project, but it's structured the same way a real team project would be, so contributing follows normal conventions.

## Setting up for development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

## Before opening a pull request

Run the same checks CI runs, locally, with one command:

```bash
make check
```

This runs `ruff` (lint), `black --check` (formatting), and the full `pytest` suite. All three must pass before a PR can merge — the GitHub Actions workflow in `.github/workflows/ci.yml` enforces this automatically on every push.

## Code style

- Formatting is handled by `black` (line length 110) — run `make format` to auto-fix.
- Linting is handled by `ruff`.
- New agent logic should be a plain function `(GraphState) -> dict`, consistent with the existing five agents in `app/agents/`, so it stays trivially unit-testable without needing the full graph.
- Business/math logic (simulation, forecasting formulas, data loading) belongs in `app/services/`, not inside an agent file — agents should orchestrate and decide, services should compute.

## Adding a new agent to the graph

1. Add the node function to `app/agents/<name>_agent.py`, following the existing pattern (read from `GraphState`, return a partial dict update, including `next_agent`).
2. Add any new state fields to `app/models/state.py`. **Make sure the field name does not collide with any node name** — LangGraph raises an error at compile time if it does (see `docs/ARCHITECTURE.md` → "Shared state design" for why this matters).
3. Register the node and its conditional edges in `app/agents/graph.py`.
4. Add unit tests in `tests/test_agents.py` and, if it changes the overall flow, an integration test in `tests/test_integration_workflow.py`.

## Tests

```bash
make test          # run the suite
make test-cov       # run the suite with a coverage report
```
