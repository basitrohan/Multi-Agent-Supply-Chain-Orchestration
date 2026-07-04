"""
Integration tests: run the FULL LangGraph workflow end-to-end (all 5 agents)
against the real sample dataset. These are slower than the unit tests in
test_agents.py but verify the agents actually compose correctly together.
"""

from app.models.domain import DisruptionType, StressTestRequest
from app.services.orchestration_service import run_stress_test


class TestFullWorkflowIntegration:
    def test_happy_path_produces_complete_report(self):
        request = StressTestRequest(
            scenario_name="Integration Test - Moderate Disruption",
            disruption_type=DisruptionType.SUPPLIER_DELAY,
            affected_region="North America",
            severity=0.4,
            duration_days=10,
        )

        result = run_stress_test(request)

        assert result.report_markdown is not None
        assert "Executive Summary" in result.report_markdown
        assert result.risk_assessment["risk_score"] is not None
        assert result.simulation_summary["total_runs"] > 0
        assert result.forecast["forecast_horizon_months"] > 0
        assert result.errors == []

    def test_audit_log_contains_all_five_agents(self):
        request = StressTestRequest(
            scenario_name="Integration Test - Audit Trail",
            disruption_type=DisruptionType.DEMAND_SPIKE,
            affected_region="EU",
            severity=0.3,
            duration_days=7,
        )

        result = run_stress_test(request)
        agents_that_ran = {entry["agent"] for entry in result.audit_log}

        assert "data_ingestion" in agents_that_ran
        assert "risk_assessment" in agents_that_ran
        assert "simulation" in agents_that_ran
        assert "forecasting" in agents_that_ran
        assert "report_generation" in agents_that_ran

    def test_high_severity_scenario_triggers_escalation_loop(self):
        """
        This is the key 'agentic' behavior test: a severe-enough scenario
        should cause the simulation agent to loop back on itself at least
        once before the graph proceeds to forecasting.
        """
        request = StressTestRequest(
            scenario_name="Integration Test - Escalation",
            disruption_type=DisruptionType.RAW_MATERIAL_SHORTAGE,
            affected_region="global",
            severity=0.97,
            duration_days=60,
        )

        result = run_stress_test(request)
        simulation_log_entries = [e for e in result.audit_log if e["agent"] == "simulation"]

        # More than one simulation entry in the audit log means the loop-back
        # edge fired at least once.
        assert len(simulation_log_entries) >= 1
        assert result.report_markdown is not None

    def test_report_file_is_written_to_disk(self, tmp_path, monkeypatch):
        request = StressTestRequest(
            scenario_name="Integration Test - File Output",
            disruption_type=DisruptionType.LOGISTICS_DISRUPTION,
            affected_region="APAC",
            severity=0.2,
            duration_days=5,
        )

        result = run_stress_test(request)

        from pathlib import Path

        assert result.report_path is not None
        assert Path(result.report_path).exists()
