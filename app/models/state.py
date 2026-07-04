"""
Agent graph state.

This is the most important file for understanding the LangGraph design.

In LangGraph, every node (agent) in the graph reads from and writes to a
single shared "state" object. Think of it as a clipboard that gets passed
from agent to agent -- each agent reads what previous agents wrote, adds
its own findings, and hands it to the next agent.

We use a TypedDict (LangGraph's recommended pattern) rather than a Pydantic
model for the graph state itself, because LangGraph merges partial updates
into this dict automatically between nodes. Pydantic models for the *data*
each field holds (RiskAssessment, SimulationSummary, etc.) still give us
type safety -- we just nest them inside the TypedDict.
"""

import operator
from typing import Annotated, Literal, TypedDict

from app.models.domain import (
    StressTestRequest,
)

AgentName = Literal[
    "data_ingestion",
    "risk_assessment",
    "simulation",
    "forecasting",
    "report_generation",
    "supervisor",
]


class AgentLogEntry(TypedDict):
    """One audit-trail entry, recording which agent ran and what it decided."""

    agent: AgentName
    message: str
    timestamp: str


class GraphState(TypedDict, total=False):
    """
    The shared state object passed between every agent node in the graph.

    Fields are intentionally optional (total=False) because early in the
    workflow most of them haven't been populated yet -- e.g. `risk_assessment`
    only exists after the Risk Assessment Agent has run.

    `Annotated[list, operator.add]` tells LangGraph: "when multiple nodes
    write to this field, append the lists together instead of overwriting."
    This is how we build the audit_log and error_log across the whole run.
    """

    # ----- Input -----
    request: StressTestRequest

    # ----- Ingested / validated supply chain data -----
    suppliers: list[dict]
    inventory: list[dict]
    data_quality_ok: bool

    # ----- Risk Assessment Agent output -----
    risk_assessment_result: dict  # serialized RiskAssessment

    # ----- Simulation Agent output -----
    scenario_outcomes: list[dict]  # serialized ScenarioOutcome list
    simulation_summary: dict  # serialized SimulationSummary
    simulation_attempt: int  # retry counter, used by the supervisor

    # ----- Forecasting Agent output -----
    forecast_result: dict  # serialized YoYForecast

    # ----- Report Generation Agent output -----
    report_markdown: str
    report_path: str

    # ----- Orchestration / control-flow metadata -----
    next_agent: AgentName | Literal["end"]
    audit_log: Annotated[list[AgentLogEntry], operator.add]
    errors: Annotated[list[str], operator.add]


def new_initial_state(request: StressTestRequest) -> GraphState:
    """Factory for a fresh GraphState at the start of a run."""
    return GraphState(
        request=request,
        simulation_attempt=0,
        audit_log=[],
        errors=[],
    )
