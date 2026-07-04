"""
API-level integration tests using FastAPI's TestClient (built on httpx).

These hit the actual route handlers in app/api/routes.py the same way a
real HTTP client would, but in-process (no need to actually start uvicorn).
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["bedrock_mode"] in {"live", "mock"}


class TestStressTestEndpoint:
    def test_valid_request_returns_full_report(self):
        payload = {
            "scenario_name": "API Test Scenario",
            "disruption_type": "port_closure",
            "affected_region": "APAC",
            "severity": 0.5,
            "duration_days": 14,
        }
        response = client.post("/api/v1/stress-test", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["report_markdown"] is not None
        assert "risk_assessment" in body
        assert "simulation_summary" in body
        assert "forecast" in body

    def test_invalid_disruption_type_returns_422(self):
        payload = {
            "scenario_name": "Bad Request Test",
            "disruption_type": "not_a_real_disruption_type",
            "affected_region": "APAC",
            "severity": 0.5,
        }
        response = client.post("/api/v1/stress-test", json=payload)
        assert response.status_code == 422

    def test_severity_out_of_range_returns_422(self):
        payload = {
            "scenario_name": "Severity Range Test",
            "disruption_type": "demand_spike",
            "affected_region": "EU",
            "severity": 1.5,  # invalid: must be 0.0-1.0
        }
        response = client.post("/api/v1/stress-test", json=payload)
        assert response.status_code == 422


class TestReportsEndpoint:
    def test_list_reports_returns_200(self):
        response = client.get("/api/v1/reports")
        assert response.status_code == 200
        assert "reports" in response.json()

    def test_get_nonexistent_report_returns_404(self):
        response = client.get("/api/v1/reports/this_report_does_not_exist_xyz")
        assert response.status_code == 404

    def test_get_report_after_creating_it(self):
        # First trigger a stress test to ensure a report exists.
        client.post(
            "/api/v1/stress-test",
            json={
                "scenario_name": "Fetchable Report Test",
                "disruption_type": "supplier_delay",
                "affected_region": "North America",
                "severity": 0.3,
            },
        )
        response = client.get("/api/v1/reports/fetchable_report_test")
        assert response.status_code == 200
        assert "report_markdown" in response.json()


class TestDataSummaryEndpoint:
    def test_returns_current_supplier_and_inventory_counts(self):
        response = client.get("/api/v1/data/summary")
        assert response.status_code == 200
        body = response.json()
        assert body["supplier_count"] > 0
        assert body["inventory_count"] > 0
        assert isinstance(body["regions"], list)
        assert isinstance(body["suppliers"], list)
        assert isinstance(body["inventory"], list)


class TestDataUploadEndpoint:
    """
    These tests monkeypatch `app.api.routes.settings.sample_data_dir` to a
    pytest tmp_path for the duration of each test. This is essential: the
    upload endpoint's whole job is to OVERWRITE the live suppliers/inventory
    JSON files, and we must never let a test run actually overwrite the
    real demo data other tests (and the live app) depend on.
    """

    def test_valid_suppliers_csv_replaces_data(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.api.routes.settings.sample_data_dir", str(tmp_path))

        csv_content = (
            b"supplier_id,name,region,reliability_score,avg_lead_time_days,monthly_capacity_units\n"
            b"SUP-TEST,Test Supplier,APAC,0.9,10,5000\n"
        )

        response = client.post(
            "/api/v1/data/upload?entity_type=suppliers",
            files={"file": ("suppliers.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["entity_type"] == "suppliers"
        assert body["records_loaded"] == 1
        assert (tmp_path / "suppliers.json").exists()

    def test_invalid_entity_type_returns_400(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.api.routes.settings.sample_data_dir", str(tmp_path))

        csv_content = b"a,b\n1,2\n"
        response = client.post(
            "/api/v1/data/upload?entity_type=not_real",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 400

    def test_malformed_csv_returns_422_with_clear_message(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.api.routes.settings.sample_data_dir", str(tmp_path))

        csv_content = b"supplier_id,name\nSUP-1,Test\n"  # missing required columns
        response = client.post(
            "/api/v1/data/upload?entity_type=suppliers",
            files={"file": ("bad.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 422
        assert "missing required column" in response.json()["detail"]
        # Confirm the malformed upload did NOT write a partial/broken file.
        assert not (tmp_path / "suppliers.json").exists()
