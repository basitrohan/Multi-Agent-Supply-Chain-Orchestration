"""
Risk Assessment Agent.

ROLE IN THE GRAPH: looks at the requested disruption scenario plus the
real inventory/supplier data and produces a structured RiskAssessment --
a risk score (0-1), a categorical risk level, and a list of concrete
vulnerabilities (low-reliability suppliers, thin inventory buffers).

This agent is rule-based (not an LLM call) by design: risk scoring needs
to be deterministic, explainable, and auditable -- exactly the kind of
thing a supply-chain stakeholder will ask "why did it say HIGH risk?"
about. The math is simple enough to defend line-by-line in an interview,
which is a feature, not a limitation.
"""

from __future__ import annotations

from app.agents.agent_utils import log_step
from app.core.logging_config import logger
from app.models.domain import RiskAssessment, StressTestRequest
from app.models.state import GraphState


def _risk_level_from_score(score: float) -> str:
    if score >= 0.75:
        return "CRITICAL"
    if score >= 0.55:
        return "HIGH"
    if score >= 0.3:
        return "MODERATE"
    return "LOW"


def risk_assessment_node(state: GraphState) -> dict:
    logger.info("[RiskAssessmentAgent] Assessing scenario risk...")

    request = (
        StressTestRequest(**state["request"]) if isinstance(state["request"], dict) else state["request"]
    )
    suppliers = state.get("suppliers", [])
    inventory = state.get("inventory", [])

    vulnerabilities: list[str] = []
    affected_suppliers: list[str] = []
    affected_skus: list[str] = []

    # 1) Flag suppliers in the affected region with below-average reliability.
    region_suppliers = [
        s
        for s in suppliers
        if request.affected_region.lower() in s["region"].lower()
        or request.affected_region.lower() == "global"
    ]
    avg_reliability = sum(s["reliability_score"] for s in suppliers) / len(suppliers) if suppliers else 0.85

    for s in region_suppliers:
        affected_suppliers.append(s["supplier_id"])
        if s["reliability_score"] < avg_reliability:
            vulnerabilities.append(
                f"Supplier {s['name']} ({s['supplier_id']}) in {s['region']} has below-average "
                f"reliability ({s['reliability_score']:.2f}) and is in the affected region."
            )

    # 2) Flag inventory items whose buffer (stock - reorder point) is thin
    #    relative to monthly demand, sourced from an affected supplier.
    affected_supplier_ids = {s["supplier_id"] for s in region_suppliers}
    for item in inventory:
        if item["primary_supplier_id"] in affected_supplier_ids:
            buffer_units = item["current_stock_units"] - item["reorder_point_units"]
            daily_demand = item["avg_monthly_demand_units"] / 30.0
            buffer_days = buffer_units / daily_demand if daily_demand > 0 else float("inf")

            affected_skus.append(item["sku"])
            if buffer_days < request.duration_days:
                vulnerabilities.append(
                    f"SKU {item['sku']} ({item['description']}) has only ~{buffer_days:.1f} days of "
                    f"buffer stock, less than the {request.duration_days}-day disruption window."
                )

    # 3) Compute a composite risk score.
    #    Weighted blend of: requested severity, fraction of suppliers exposed,
    #    and fraction of SKUs with insufficient buffer.
    supplier_exposure_ratio = len(region_suppliers) / len(suppliers) if suppliers else 0.5
    skus_at_risk_ratio = (
        sum(1 for v in vulnerabilities if v.startswith("SKU")) / len(inventory) if inventory else 0.5
    )

    risk_score = round(
        0.45 * request.severity + 0.25 * supplier_exposure_ratio + 0.30 * skus_at_risk_ratio,
        3,
    )
    risk_score = min(max(risk_score, 0.0), 1.0)
    risk_level = _risk_level_from_score(risk_score)

    assessment = RiskAssessment(
        risk_score=risk_score,
        risk_level=risk_level,
        key_vulnerabilities=vulnerabilities or ["No significant vulnerabilities identified."],
        affected_suppliers=affected_suppliers,
        affected_skus=affected_skus,
    )

    logger.info(
        f"[RiskAssessmentAgent] risk_score={risk_score} level={risk_level} vulnerabilities={len(vulnerabilities)}"
    )

    return {
        "risk_assessment_result": assessment.model_dump(),
        "audit_log": log_step(
            "risk_assessment",
            f"Computed risk_score={risk_score} ({risk_level}) with {len(vulnerabilities)} flagged vulnerabilities.",
        ),
        "next_agent": "simulation",
    }
