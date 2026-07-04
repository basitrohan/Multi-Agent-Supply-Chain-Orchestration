"""
Forecasting Agent.

ROLE IN THE GRAPH: turns the simulation's revenue-impact numbers into a
predictive Year-over-Year (YoY) performance forecast -- directly matching
the resume bullet's "generating predictive YoY performance reports."

APPROACH: we model a baseline YoY growth rate (what the business would
have done with no disruption) and then apply the simulated stress impact
month-by-month, tapering off as the disruption resolves and recovery
happens (using the avg_recovery_time_days from the simulation). This is a
deliberately transparent, formula-driven forecast rather than an opaque
ML model -- appropriate for a project you need to explain confidently and
quickly, and realistic for an early-stage "agentic forecasting" feature
that a team would later swap for a trained time-series model.
"""

from __future__ import annotations

from app.agents.agent_utils import log_step
from app.core.config import get_settings
from app.core.logging_config import logger
from app.models.domain import StressTestRequest, YoYForecast
from app.models.state import GraphState

settings = get_settings()

# Assumed baseline (no-disruption) YoY growth rate for the business.
# In a real system this would come from a finance/BI data warehouse --
# here it's a clearly-labeled constant so the assumption is explicit.
BASELINE_YOY_GROWTH_PCT = 8.0
ASSUMED_ANNUAL_REVENUE_USD = 50_000_000


def forecasting_node(state: GraphState) -> dict:
    logger.info("[ForecastingAgent] Building YoY predictive forecast...")

    request = (
        StressTestRequest(**state["request"]) if isinstance(state["request"], dict) else state["request"]
    )
    summary = state.get("simulation_summary", {})

    expected_impact = summary.get("expected_revenue_impact_usd", 0.0)
    recovery_days = summary.get("avg_recovery_time_days", 0.0) or 1.0

    horizon = settings.forecast_horizon_months
    monthly_baseline_revenue = ASSUMED_ANNUAL_REVENUE_USD / 12 * (1 + BASELINE_YOY_GROWTH_PCT / 100)

    # Spread the simulated impact over the disruption window, then taper
    # off over the recovery period using a simple linear decay.
    disruption_months = max(1, round(request.duration_days / 30))
    recovery_months = max(1, round(recovery_days / 30))

    monthly_projection: list[dict] = []
    stressed_total = 0.0
    baseline_total = 0.0

    for month in range(1, horizon + 1):
        baseline_revenue = monthly_baseline_revenue
        baseline_total += baseline_revenue

        if month <= disruption_months:
            impact_this_month = expected_impact / disruption_months
        elif month <= disruption_months + recovery_months:
            decay_progress = (month - disruption_months) / recovery_months
            impact_this_month = (expected_impact / disruption_months) * (1 - decay_progress)
        else:
            impact_this_month = 0.0

        stressed_revenue = max(0.0, baseline_revenue - impact_this_month)
        stressed_total += stressed_revenue

        monthly_projection.append(
            {
                "month": month,
                "baseline_revenue_usd": round(baseline_revenue, 2),
                "stressed_revenue_usd": round(stressed_revenue, 2),
                "impact_usd": round(impact_this_month, 2),
            }
        )

    baseline_yoy = BASELINE_YOY_GROWTH_PCT
    prior_year_revenue = ASSUMED_ANNUAL_REVENUE_USD
    stressed_yoy = round(((stressed_total - prior_year_revenue) / prior_year_revenue) * 100, 2)
    growth_delta = round(stressed_yoy - baseline_yoy, 2)

    forecast = YoYForecast(
        baseline_yoy_growth_pct=baseline_yoy,
        stressed_yoy_growth_pct=stressed_yoy,
        growth_delta_pct=growth_delta,
        forecast_horizon_months=horizon,
        monthly_projection=monthly_projection,
    )

    logger.info(
        f"[ForecastingAgent] baseline_yoy={baseline_yoy}% stressed_yoy={stressed_yoy}% "
        f"delta={growth_delta}pts over {horizon} months"
    )

    return {
        "forecast_result": forecast.model_dump(),
        "audit_log": log_step(
            "forecasting",
            f"Projected {horizon}-month YoY forecast: baseline={baseline_yoy:+.1f}%, "
            f"stressed={stressed_yoy:+.1f}% (delta {growth_delta:+.1f} pts).",
        ),
        "next_agent": "report_generation",
    }
