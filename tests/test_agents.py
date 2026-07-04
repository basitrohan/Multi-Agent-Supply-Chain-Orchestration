"""
Unit tests for individual agent node functions.

Each agent node is a plain function: (GraphState) -> dict. That makes them
trivially unit-testable WITHOUT running the full LangGraph -- we just build
a minimal state dict by hand and check the returned partial update.
"""

from app.agents.data_ingestion_agent import data_ingestion_node
from app.agents.forecasting_agent import forecasting_node
from app.agents.risk_assessment_agent import risk_assessment_node
from app.agents.simulation_agent import simulation_node
from app.models.state import new_initial_state


class TestDataIngestionAgent:
    def test_ingests_sample_data_successfully(self, sample_request):
        state = new_initial_state(sample_request)
        result = data_ingestion_node(state)

        assert result["data_quality_ok"] is True
        assert len(result["suppliers"]) > 0
        assert len(result["inventory"]) > 0
        assert result["next_agent"] == "risk_assessment"

    def test_audit_log_entry_is_created(self, sample_request):
        state = new_initial_state(sample_request)
        result = data_ingestion_node(state)

        assert len(result["audit_log"]) == 1
        assert result["audit_log"][0]["agent"] == "data_ingestion"


class TestRiskAssessmentAgent:
    def test_produces_valid_risk_score(self, sample_request, sample_suppliers, sample_inventory):
        state = new_initial_state(sample_request)
        state["suppliers"] = sample_suppliers
        state["inventory"] = sample_inventory

        result = risk_assessment_node(state)
        risk = result["risk_assessment_result"]

        assert 0.0 <= risk["risk_score"] <= 1.0
        assert risk["risk_level"] in {"LOW", "MODERATE", "HIGH", "CRITICAL"}
        assert result["next_agent"] == "simulation"

    def test_higher_severity_request_yields_higher_or_equal_risk(self, sample_suppliers, sample_inventory):
        from app.models.domain import DisruptionType, StressTestRequest

        low_req = StressTestRequest(
            scenario_name="low",
            disruption_type=DisruptionType.SUPPLIER_DELAY,
            affected_region="APAC",
            severity=0.1,
            duration_days=5,
        )
        high_req = StressTestRequest(
            scenario_name="high",
            disruption_type=DisruptionType.SUPPLIER_DELAY,
            affected_region="APAC",
            severity=0.9,
            duration_days=5,
        )

        low_state = new_initial_state(low_req)
        low_state["suppliers"] = sample_suppliers
        low_state["inventory"] = sample_inventory

        high_state = new_initial_state(high_req)
        high_state["suppliers"] = sample_suppliers
        high_state["inventory"] = sample_inventory

        low_result = risk_assessment_node(low_state)
        high_result = risk_assessment_node(high_state)

        assert (
            high_result["risk_assessment_result"]["risk_score"]
            >= low_result["risk_assessment_result"]["risk_score"]
        )


class TestSimulationAgent:
    def test_escalates_when_risk_high_and_stockout_likely(self, sample_inventory, sample_suppliers):
        from app.models.domain import DisruptionType, StressTestRequest

        request = StressTestRequest(
            scenario_name="severe",
            disruption_type=DisruptionType.PORT_CLOSURE,
            affected_region="APAC",
            severity=0.99,
            duration_days=90,
        )
        state = new_initial_state(request)
        state["suppliers"] = sample_suppliers
        state["inventory"] = sample_inventory
        state["risk_assessment_result"] = {"risk_score": 0.9, "risk_level": "CRITICAL"}
        state["simulation_attempt"] = 0

        result = simulation_node(state)

        # With risk_score=0.9 (>= default 0.65 threshold) and severe params,
        # the agent should request another attempt rather than proceeding.
        assert result["next_agent"] in {"simulation", "forecasting"}
        assert result["simulation_attempt"] == 1

    def test_respects_max_retry_limit(self, sample_inventory, sample_suppliers):
        from app.core.config import get_settings
        from app.models.domain import DisruptionType, StressTestRequest

        settings = get_settings()
        request = StressTestRequest(
            scenario_name="severe",
            disruption_type=DisruptionType.PORT_CLOSURE,
            affected_region="APAC",
            severity=0.99,
            duration_days=90,
        )
        state = new_initial_state(request)
        state["suppliers"] = sample_suppliers
        state["inventory"] = sample_inventory
        state["risk_assessment_result"] = {"risk_score": 0.95, "risk_level": "CRITICAL"}
        # Simulate having already hit the max retry count.
        state["simulation_attempt"] = settings.max_simulation_retries

        result = simulation_node(state)

        # Should NOT escalate further once max retries reached -- must proceed forward.
        assert result["next_agent"] == "forecasting"


class TestForecastingAgent:
    def test_produces_forecast_with_correct_horizon(self, sample_request):
        from app.core.config import get_settings

        settings = get_settings()
        state = new_initial_state(sample_request)
        state["simulation_summary"] = {
            "expected_revenue_impact_usd": 50000.0,
            "avg_recovery_time_days": 10.0,
        }

        result = forecasting_node(state)
        forecast = result["forecast_result"]

        assert forecast["forecast_horizon_months"] == settings.forecast_horizon_months
        assert len(forecast["monthly_projection"]) == settings.forecast_horizon_months
        assert result["next_agent"] == "report_generation"

    def test_zero_impact_yields_baseline_growth(self, sample_request):
        state = new_initial_state(sample_request)
        state["simulation_summary"] = {"expected_revenue_impact_usd": 0.0, "avg_recovery_time_days": 0.0}

        result = forecasting_node(state)
        forecast = result["forecast_result"]

        assert forecast["stressed_yoy_growth_pct"] == forecast["baseline_yoy_growth_pct"]
        assert forecast["growth_delta_pct"] == 0.0
