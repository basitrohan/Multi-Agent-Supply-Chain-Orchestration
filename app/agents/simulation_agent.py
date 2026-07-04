"""
Simulation Agent.

ROLE IN THE GRAPH: runs the Monte Carlo stress test (via
StressTestSimulationEngine) and decides what happens next based on the
result -- this is the clearest example of "agentic" (non-linear) behavior
in the whole system:

    - If the resulting risk is at/above settings.risk_escalation_threshold
      AND we haven't already retried too many times, the agent requests a
      RE-RUN with a larger number of simulation iterations (more Monte
      Carlo runs => tighter confidence interval on the tail-risk numbers)
      before trusting the result enough to forecast and report on it.
    - Otherwise it proceeds forward to the Forecasting Agent.

This conditional retry/escalation is exactly the behavior a plain linear
chain (or a static ETL pipeline) cannot express -- it's why the project
uses LangGraph (a graph with conditional edges) instead of a simple
sequential script.
"""

from __future__ import annotations

from app.agents.agent_utils import log_step
from app.core.config import get_settings
from app.core.logging_config import logger
from app.models.domain import StressTestRequest
from app.models.state import GraphState
from app.services.simulation_engine import StressTestSimulationEngine

settings = get_settings()


def simulation_node(state: GraphState) -> dict:
    attempt = state.get("simulation_attempt", 0) + 1
    logger.info(f"[SimulationAgent] Starting simulation attempt #{attempt}...")

    request = (
        StressTestRequest(**state["request"]) if isinstance(state["request"], dict) else state["request"]
    )
    inventory = state.get("inventory", [])
    suppliers = state.get("suppliers", [])
    risk_assessment = state.get("risk_assessment_result", {})

    # Escalate fidelity (more Monte Carlo runs) on retry attempts so the
    # re-simulation actually gives a more *confident* answer, not just a
    # repeated roll of the dice.
    n_runs = settings.simulation_runs * attempt

    engine = StressTestSimulationEngine(seed=42 + attempt)  # vary seed slightly per attempt
    outcomes, summary = engine.run(request, inventory, suppliers, n_runs=n_runs)

    risk_score = risk_assessment.get("risk_score", 0.0)
    should_escalate = (
        risk_score >= settings.risk_escalation_threshold
        and attempt <= settings.max_simulation_retries
        and summary.stockout_probability > 0.5
    )

    if should_escalate:
        logger.warning(
            f"[SimulationAgent] High risk_score={risk_score} with stockout_probability="
            f"{summary.stockout_probability:.2%} -> escalating to a higher-fidelity re-simulation "
            f"(attempt {attempt} of max {settings.max_simulation_retries})."
        )
        return {
            "scenario_outcomes": [o.model_dump() for o in outcomes[-50:]],  # keep a sample, not all 1000s
            "simulation_summary": summary.model_dump(),
            "simulation_attempt": attempt,
            "audit_log": log_step(
                "simulation",
                f"Attempt {attempt}: stockout_probability={summary.stockout_probability:.2%} exceeds "
                f"confidence threshold given risk_score={risk_score}. Escalating to re-simulate with "
                f"more iterations before forecasting.",
            ),
            "next_agent": "simulation",  # loop back to self via conditional edge
        }

    logger.info(
        f"[SimulationAgent] Simulation accepted on attempt {attempt} "
        f"(stockout_probability={summary.stockout_probability:.2%})"
    )
    return {
        "scenario_outcomes": [o.model_dump() for o in outcomes[-50:]],
        "simulation_summary": summary.model_dump(),
        "simulation_attempt": attempt,
        "audit_log": log_step(
            "simulation",
            f"Attempt {attempt} accepted with {n_runs} runs. "
            f"stockout_probability={summary.stockout_probability:.2%}, "
            f"expected_impact=${summary.expected_revenue_impact_usd:,.0f}.",
        ),
        "next_agent": "forecasting",
    }
