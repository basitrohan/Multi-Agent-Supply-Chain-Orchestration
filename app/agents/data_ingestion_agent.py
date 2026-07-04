"""
Data Ingestion Agent.

ROLE IN THE GRAPH: entry point. Pulls current supplier + inventory data
and validates it before anything else happens.

WHY THIS IS AN "AGENT" AND NOT JUST AN ETL STEP: it makes a decision.
If validation fails, it sets `data_quality_ok = False` and the graph's
conditional routing (see app/agents/graph.py) sends the run straight to
an error-exit instead of wasting compute on simulating garbage data.
A static ETL pipeline would typically either crash or silently propagate
bad data -- this agent actively gates the rest of the pipeline.
"""

from __future__ import annotations

from app.agents.agent_utils import log_step
from app.core.config import get_settings
from app.core.logging_config import logger
from app.models.state import GraphState
from app.services.data_loader import DataValidationError, SupplyChainDataLoader

settings = get_settings()


def data_ingestion_node(state: GraphState) -> dict:
    """LangGraph node function: (state) -> partial state update."""
    logger.info("[DataIngestionAgent] Starting ingestion...")
    loader = SupplyChainDataLoader(data_dir=settings.sample_data_dir)

    try:
        suppliers = loader.load_suppliers()
        inventory = loader.load_inventory()
    except DataValidationError as exc:
        logger.error(f"[DataIngestionAgent] Failed to load data: {exc}")
        return {
            "data_quality_ok": False,
            "errors": [f"Data ingestion failed: {exc}"],
            "audit_log": log_step("data_ingestion", f"FAILED to load source data: {exc}"),
            "next_agent": "end",
        }

    is_valid, problems = loader.validate_referential_integrity(suppliers, inventory)

    if not is_valid:
        return {
            "suppliers": [s.model_dump() for s in suppliers],
            "inventory": [i.model_dump() for i in inventory],
            "data_quality_ok": False,
            "errors": problems,
            "audit_log": log_step(
                "data_ingestion",
                f"Validation FAILED with {len(problems)} issue(s); routing to error exit.",
            ),
            "next_agent": "end",
        }

    logger.info(
        f"[DataIngestionAgent] Loaded {len(suppliers)} suppliers and {len(inventory)} SKUs successfully."
    )
    return {
        "suppliers": [s.model_dump() for s in suppliers],
        "inventory": [i.model_dump() for i in inventory],
        "data_quality_ok": True,
        "audit_log": log_step(
            "data_ingestion",
            f"Ingested {len(suppliers)} suppliers and {len(inventory)} SKUs. Validation passed.",
        ),
        "next_agent": "risk_assessment",
    }
