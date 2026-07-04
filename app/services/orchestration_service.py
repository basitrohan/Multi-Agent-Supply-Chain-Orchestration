"""
Orchestration service: the bridge between the FastAPI layer and the
LangGraph agent workflow.

WHY THIS LAYER EXISTS
-----------------------
FastAPI route handlers should stay thin (parse request -> call a service
-> return response). This module is that "service": it owns the lifecycle
of a single stress-test run -- building the initial graph state, invoking
the compiled LangGraph, and shaping the final state into a clean response
object. Keeping this logic out of app/api/routes.py means the orchestration
logic is independently testable and reusable (e.g. from a CLI script or a
background worker) without needing an HTTP request at all.
"""

from __future__ import annotations

import uuid

from app.agents.graph import supply_chain_graph
from app.core.logging_config import logger
from app.models.domain import StressTestRequest
from app.models.state import new_initial_state


class OrchestrationResult:
    """Plain container for everything the API layer needs to build a response."""

    def __init__(self, run_id: str, final_state: dict) -> None:
        self.run_id = run_id
        self.final_state = final_state

    @property
    def succeeded(self) -> bool:
        return (
            bool(self.final_state.get("report_markdown"))
            and self.final_state.get("data_quality_ok") is not False
        )

    @property
    def report_markdown(self) -> str | None:
        return self.final_state.get("report_markdown")

    @property
    def report_path(self) -> str | None:
        return self.final_state.get("report_path")

    @property
    def audit_log(self) -> list[dict]:
        return self.final_state.get("audit_log", [])

    @property
    def errors(self) -> list[str]:
        return self.final_state.get("errors", [])

    @property
    def risk_assessment(self) -> dict:
        return self.final_state.get("risk_assessment_result", {})

    @property
    def simulation_summary(self) -> dict:
        return self.final_state.get("simulation_summary", {})

    @property
    def forecast(self) -> dict:
        return self.final_state.get("forecast_result", {})


def run_stress_test(request: StressTestRequest) -> OrchestrationResult:
    """
    Execute one full multi-agent stress-test workflow synchronously and
    return its result. This is the single function the FastAPI route
    handler calls.
    """
    run_id = str(uuid.uuid4())
    logger.info(f"=== Starting stress-test run {run_id} for scenario '{request.scenario_name}' ===")

    initial_state = new_initial_state(request)
    final_state = supply_chain_graph.invoke(initial_state)

    logger.info(f"=== Completed stress-test run {run_id} ===")
    return OrchestrationResult(run_id=run_id, final_state=final_state)
