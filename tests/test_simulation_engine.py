"""
Unit tests for the Monte Carlo simulation engine.

These tests deliberately use small, fixed sample data (not the full
data/sample/*.json files) so they're fast, isolated, and don't depend on
the order or content of the project's demo dataset.
"""

from app.models.domain import DisruptionType, StressTestRequest
from app.services.simulation_engine import StressTestSimulationEngine


class TestStressTestSimulationEngine:
    def test_run_returns_correct_number_of_outcomes(self, sample_request, sample_inventory, sample_suppliers):
        engine = StressTestSimulationEngine(seed=1)
        outcomes, summary = engine.run(sample_request, sample_inventory, sample_suppliers, n_runs=50)

        assert len(outcomes) == 50
        assert summary.total_runs == 50

    def test_higher_severity_increases_stockout_probability(self, sample_inventory, sample_suppliers):
        engine_low = StressTestSimulationEngine(seed=1)
        engine_high = StressTestSimulationEngine(seed=1)

        low_severity_request = StressTestRequest(
            scenario_name="Low severity",
            disruption_type=DisruptionType.SUPPLIER_DELAY,
            affected_region="APAC",
            severity=0.05,
            duration_days=5,
        )
        high_severity_request = StressTestRequest(
            scenario_name="High severity",
            disruption_type=DisruptionType.SUPPLIER_DELAY,
            affected_region="APAC",
            severity=0.95,
            duration_days=60,
        )

        _, low_summary = engine_low.run(low_severity_request, sample_inventory, sample_suppliers, n_runs=200)
        _, high_summary = engine_high.run(
            high_severity_request, sample_inventory, sample_suppliers, n_runs=200
        )

        assert high_summary.stockout_probability >= low_summary.stockout_probability
        assert high_summary.expected_revenue_impact_usd >= low_summary.expected_revenue_impact_usd

    def test_summary_statistics_are_internally_consistent(
        self, sample_request, sample_inventory, sample_suppliers
    ):
        engine = StressTestSimulationEngine(seed=7)
        _, summary = engine.run(sample_request, sample_inventory, sample_suppliers, n_runs=100)

        # P90 should always be >= the mean (it's a higher percentile of a non-negative distribution)
        assert summary.p90_revenue_impact_usd >= summary.expected_revenue_impact_usd
        # Worst case should always be >= P90
        assert summary.worst_case_revenue_impact_usd >= summary.p90_revenue_impact_usd
        # Probabilities must be valid
        assert 0.0 <= summary.stockout_probability <= 1.0

    def test_unknown_supplier_reference_is_skipped_gracefully(self, sample_request, sample_suppliers):
        inventory_with_bad_ref = [
            {
                "sku": "SKU-ORPHAN",
                "description": "Orphaned SKU",
                "current_stock_units": 100,
                "reorder_point_units": 10,
                "avg_monthly_demand_units": 50,
                "unit_cost_usd": 1.0,
                "primary_supplier_id": "SUP-DOES-NOT-EXIST",
            }
        ]
        engine = StressTestSimulationEngine(seed=1)
        # Should not raise -- the engine just skips items with unknown suppliers.
        outcomes, summary = engine.run(sample_request, inventory_with_bad_ref, sample_suppliers, n_runs=10)
        assert len(outcomes) == 10
        assert summary.expected_revenue_impact_usd == 0.0

    def test_reproducible_with_fixed_seed(self, sample_request, sample_inventory, sample_suppliers):
        engine_a = StressTestSimulationEngine(seed=99)
        engine_b = StressTestSimulationEngine(seed=99)

        _, summary_a = engine_a.run(sample_request, sample_inventory, sample_suppliers, n_runs=30)
        _, summary_b = engine_b.run(sample_request, sample_inventory, sample_suppliers, n_runs=30)

        assert summary_a.expected_revenue_impact_usd == summary_b.expected_revenue_impact_usd
        assert summary_a.stockout_probability == summary_b.stockout_probability
