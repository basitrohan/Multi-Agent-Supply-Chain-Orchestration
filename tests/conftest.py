"""Shared pytest fixtures for the test suite."""

import pytest

from app.models.domain import DisruptionType, StressTestRequest


@pytest.fixture
def sample_suppliers() -> list[dict]:
    return [
        {
            "supplier_id": "SUP-A",
            "name": "Test Supplier A",
            "region": "APAC",
            "reliability_score": 0.9,
            "avg_lead_time_days": 10,
            "monthly_capacity_units": 10000,
        },
        {
            "supplier_id": "SUP-B",
            "name": "Test Supplier B",
            "region": "North America",
            "reliability_score": 0.6,
            "avg_lead_time_days": 20,
            "monthly_capacity_units": 5000,
        },
    ]


@pytest.fixture
def sample_inventory() -> list[dict]:
    return [
        {
            "sku": "SKU-A",
            "description": "Widget A",
            "current_stock_units": 1000,
            "reorder_point_units": 200,
            "avg_monthly_demand_units": 600,
            "unit_cost_usd": 5.0,
            "primary_supplier_id": "SUP-A",
        },
        {
            "sku": "SKU-B",
            "description": "Widget B",
            "current_stock_units": 100,
            "reorder_point_units": 80,
            "avg_monthly_demand_units": 300,
            "unit_cost_usd": 12.0,
            "primary_supplier_id": "SUP-B",
        },
    ]


@pytest.fixture
def sample_request() -> StressTestRequest:
    return StressTestRequest(
        scenario_name="Unit Test Scenario",
        disruption_type=DisruptionType.SUPPLIER_DELAY,
        affected_region="APAC",
        severity=0.5,
        duration_days=14,
    )
