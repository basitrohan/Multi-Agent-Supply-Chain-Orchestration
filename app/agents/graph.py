"""
LangGraph workflow definition.

THIS IS THE FILE THAT MAKES THE SYSTEM "AGENTIC."

A static ETL pipeline is a straight line: Step 1 -> Step 2 -> Step 3.
This system is a GRAPH: nodes (agents) are connected by CONDITIONAL edges,
meaning the path through the system is decided at runtime based on what
each agent finds:

    data_ingestion --(data bad?)--> END (error report)
                   --(data ok?)---> risk_assessment
                                        |
                                        v
                                    simulation <---+
                                        |          | (escalate: risk too
                                        |          |  high, retry with more
                                        v          |  Monte Carlo runs)
                              (risk acceptable?) ---+
                                        |
                                        v
                                  forecasting
                                        |
                                        v
                              report_generation
                                        |
                                        v
                                      END

This loop-back edge from `simulation` to itself (the retry/escalation
behavior) is the textbook example of why you'd reach for LangGraph instead
of LangChain's simpler sequential chains -- chains can't easily express
"go back and redo step 3 with different parameters before continuing."

HOW ROUTING WORKS
------------------
Every agent node writes `next_agent` into the shared state (see
app/models/state.py). After each node runs, LangGraph calls our routing
function `route_next()`, which just reads that field and returns the name
of the next node (or "end"). This keeps routing logic in ONE place instead
of scattering `if/else` graph-wiring across every agent.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.data_ingestion_agent import data_ingestion_node
from app.agents.forecasting_agent import forecasting_node
from app.agents.report_generation_agent import report_generation_node
from app.agents.risk_assessment_agent import risk_assessment_node
from app.agents.simulation_agent import simulation_node
from app.core.logging_config import logger
from app.models.state import GraphState


def route_next(state: GraphState) -> str:
    """Read the `next_agent` field each node sets and route accordingly."""
    next_agent = state.get("next_agent", "end")
    if next_agent == "end":
        return END
    return next_agent


def build_graph():
    """
    Construct and compile the LangGraph StateGraph.

    Returns a compiled graph (a `CompiledStateGraph`) with a `.invoke()`
    method, exactly like a LangChain Runnable -- which is what lets the
    FastAPI layer call it with a single, simple `.invoke(initial_state)`.
    """
    graph = StateGraph(GraphState)

    # ----- Register nodes -----
    graph.add_node("data_ingestion", data_ingestion_node)
    graph.add_node("risk_assessment", risk_assessment_node)
    graph.add_node("simulation", simulation_node)
    graph.add_node("forecasting", forecasting_node)
    graph.add_node("report_generation", report_generation_node)

    # ----- Entry point -----
    graph.set_entry_point("data_ingestion")

    # ----- Conditional edges -----
    # Every node's possible destinations are listed explicitly (LangGraph
    # requires this mapping for conditional edges) so the graph structure
    # is fully visible just by reading this file.
    graph.add_conditional_edges(
        "data_ingestion",
        route_next,
        {"risk_assessment": "risk_assessment", END: END},
    )
    graph.add_conditional_edges(
        "risk_assessment",
        route_next,
        {"simulation": "simulation", END: END},
    )
    graph.add_conditional_edges(
        "simulation",
        route_next,
        {"simulation": "simulation", "forecasting": "forecasting", END: END},
    )
    graph.add_conditional_edges(
        "forecasting",
        route_next,
        {"report_generation": "report_generation", END: END},
    )
    graph.add_conditional_edges(
        "report_generation",
        route_next,
        {END: END},
    )

    compiled = graph.compile()
    logger.info("LangGraph workflow compiled successfully.")
    return compiled


# Module-level singleton -- compiled once, reused across requests.
supply_chain_graph = build_graph()
