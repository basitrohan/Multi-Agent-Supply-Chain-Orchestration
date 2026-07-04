"""
Monte Carlo stress-test simulation engine.

WHY A SEPARATE SERVICE FILE
----------------------------
The "Simulation Agent" (app/agents/simulation_agent.py) is responsible for
*orchestration*: deciding when to run the simulation, how to interpret the
results, and what to do next in the graph. The actual *math* of running a
Monte Carlo simulation has nothing to do with LangGraph -- it's pure,
testable, reusable logic. So it lives here, in the service layer, and the
agent simply calls it. This separation is what lets us unit-test the
simulation math in isolation (see tests/test_simulation_engine.py) without
spinning up any agent or graph machinery.

THE MODEL (kept intentionally simple but realistic)
-----------------------------------------------------
For each Monte Carlo run we simulate:
  1. A random lead-time delay drawn from a distribution shaped by the
     disruption severity and the supplier's baseline reliability.
  2. Whether that delay causes inventory to fall below the reorder point
     before replenishment arrives (a "stockout").
  3. The resulting revenue impact (lost sales) and recovery time.

This is a simplified discrete-event style simulation -- exactly the kind of
explainable, defensible model you want for an interview: not a black box,
every number traces back to an assumption you can state out loud.
"""

from __future__ import annotations

import numpy as np

from app.core.logging_config import logger
from app.models.domain import ScenarioOutcome, SimulationSummary, StressTestRequest


class StressTestSimulationEngine:
    """Runs Monte Carlo stress-test simulations over supply chain data."""

    def __init__(self, seed: int | None = 42) -> None:
        # Fixed seed by default -> reproducible results for demos/tests.
        # Pass seed=None for true randomness in production.
        self._rng = np.random.default_rng(seed)

    def run(
        self,
        request: StressTestRequest,
        inventory: list[dict],
        suppliers: list[dict],
        n_runs: int,
    ) -> tuple[list[ScenarioOutcome], SimulationSummary]:
        """
        Execute `n_runs` Monte Carlo iterations for the given disruption
        scenario against the provided inventory/supplier snapshot.
        """
        logger.info(
            f"Running stress-test simulation | scenario='{request.scenario_name}' | "
            f"runs={n_runs} | severity={request.severity}"
        )

        supplier_lookup = {s["supplier_id"]: s for s in suppliers}
        outcomes: list[ScenarioOutcome] = []

        for run_id in range(n_runs):
            outcome = self._simulate_single_run(run_id, request, inventory, supplier_lookup)
            outcomes.append(outcome)

        summary = self._summarize(outcomes)
        logger.info(
            f"Simulation complete | stockout_probability={summary.stockout_probability:.2%} | "
            f"expected_impact=${summary.expected_revenue_impact_usd:,.0f}"
        )
        return outcomes, summary

    # ------------------------------------------------------------------ #
    # Internal mechanics
    # ------------------------------------------------------------------ #

    def _simulate_single_run(
        self,
        run_id: int,
        request: StressTestRequest,
        inventory: list[dict],
        supplier_lookup: dict[str, dict],
    ) -> ScenarioOutcome:
        # Severity (0-1) widens both the mean and variance of the delay distribution.
        base_delay_days = request.duration_days * request.severity

        total_revenue_impact = 0.0
        any_stockout = False
        min_days_to_stockout: float | None = None
        recovery_times: list[float] = []

        for item in inventory:
            supplier = supplier_lookup.get(item["primary_supplier_id"])
            if supplier is None:
                continue

            reliability = supplier.get("reliability_score", 0.8)
            # Lower reliability => larger random delay on top of the base disruption delay.
            jitter_scale = max(0.5, (1.0 - reliability) * 10)
            extra_delay = self._rng.gamma(shape=2.0, scale=jitter_scale)
            effective_delay_days = base_delay_days + extra_delay

            daily_demand = item["avg_monthly_demand_units"] / 30.0
            usable_buffer_units = max(0, item["current_stock_units"] - item["reorder_point_units"])
            days_of_buffer = (usable_buffer_units / daily_demand) if daily_demand > 0 else float("inf")

            stockout = effective_delay_days > days_of_buffer
            if stockout:
                any_stockout = True
                days_to_stockout = days_of_buffer
                if min_days_to_stockout is None or days_to_stockout < min_days_to_stockout:
                    min_days_to_stockout = days_to_stockout

                shortfall_days = effective_delay_days - days_of_buffer
                lost_units = shortfall_days * daily_demand
                revenue_impact = lost_units * item["unit_cost_usd"] * 2.2  # markup proxy for lost sale value
                total_revenue_impact += revenue_impact

                recovery_times.append(shortfall_days * self._rng.uniform(0.8, 1.4))

        avg_recovery = float(np.mean(recovery_times)) if recovery_times else 0.0

        return ScenarioOutcome(
            run_id=run_id,
            stockout_occurred=any_stockout,
            days_to_stockout=min_days_to_stockout,
            revenue_impact_usd=round(total_revenue_impact, 2),
            recovery_time_days=round(avg_recovery, 2),
        )

    @staticmethod
    def _summarize(outcomes: list[ScenarioOutcome]) -> SimulationSummary:
        impacts = np.array([o.revenue_impact_usd for o in outcomes])
        recoveries = np.array([o.recovery_time_days for o in outcomes if o.recovery_time_days > 0])
        stockouts = np.array([o.stockout_occurred for o in outcomes])

        return SimulationSummary(
            total_runs=len(outcomes),
            stockout_probability=float(stockouts.mean()) if len(stockouts) else 0.0,
            expected_revenue_impact_usd=round(float(impacts.mean()), 2) if len(impacts) else 0.0,
            p90_revenue_impact_usd=round(float(np.percentile(impacts, 90)), 2) if len(impacts) else 0.0,
            avg_recovery_time_days=round(float(recoveries.mean()), 2) if len(recoveries) else 0.0,
            worst_case_revenue_impact_usd=round(float(impacts.max()), 2) if len(impacts) else 0.0,
        )
