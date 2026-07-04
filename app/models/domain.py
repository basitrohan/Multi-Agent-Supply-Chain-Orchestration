"""
Domain models for supply chain entities.

These Pydantic models describe the *business data* the system works with:
suppliers, SKUs/inventory, and the incoming stress-test request. Keeping
them separate from the agent "state" models (see app/models/state.py) is a
deliberate separation of concerns:

    domain.py  -> "what is a supplier, what is an SKU"   (the nouns)
    state.py   -> "what does the agent graph pass around" (the workflow)
"""

from enum import Enum

from pydantic import BaseModel, Field


class DisruptionType(str, Enum):
    """Categories of supply chain disruption the simulation engine understands."""

    SUPPLIER_DELAY = "supplier_delay"
    DEMAND_SPIKE = "demand_spike"
    PORT_CLOSURE = "port_closure"
    RAW_MATERIAL_SHORTAGE = "raw_material_shortage"
    LOGISTICS_DISRUPTION = "logistics_disruption"


class Supplier(BaseModel):
    """A single supplier node in the supply chain network."""

    supplier_id: str
    name: str
    region: str
    reliability_score: float = Field(ge=0.0, le=1.0, description="0=unreliable, 1=perfectly reliable")
    avg_lead_time_days: int = Field(ge=0)
    monthly_capacity_units: int = Field(ge=0)


class InventoryItem(BaseModel):
    """A single SKU tracked in the supply chain."""

    sku: str
    description: str
    current_stock_units: int = Field(ge=0)
    reorder_point_units: int = Field(ge=0)
    avg_monthly_demand_units: int = Field(ge=0)
    unit_cost_usd: float = Field(ge=0.0)
    primary_supplier_id: str


class StressTestRequest(BaseModel):
    """
    The payload a client sends to trigger a stress-test simulation.

    This is intentionally simple at the API boundary -- the heavy lifting
    (which agents run, in what order, with what retries) is an internal
    concern decided by the LangGraph workflow, not the caller.
    """

    scenario_name: str = Field(..., examples=["West Coast Port Closure - Q3"])
    disruption_type: DisruptionType
    affected_region: str = Field(..., examples=["APAC", "North America", "EU"])
    severity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="0=minor disruption, 1=catastrophic disruption",
    )
    duration_days: int = Field(default=14, ge=1, le=365)
    notes: str | None = Field(default=None, description="Optional free-text context for the agents")


class ScenarioOutcome(BaseModel):
    """Result of a single Monte Carlo simulation run."""

    run_id: int
    stockout_occurred: bool
    days_to_stockout: float | None
    revenue_impact_usd: float
    recovery_time_days: float


class RiskAssessment(BaseModel):
    """Output of the Risk Assessment Agent."""

    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: str  # LOW | MODERATE | HIGH | CRITICAL
    key_vulnerabilities: list[str]
    affected_suppliers: list[str]
    affected_skus: list[str]


class SimulationSummary(BaseModel):
    """Aggregated output of the Simulation Agent across all Monte Carlo runs."""

    total_runs: int
    stockout_probability: float
    expected_revenue_impact_usd: float
    p90_revenue_impact_usd: float
    avg_recovery_time_days: float
    worst_case_revenue_impact_usd: float


class YoYForecast(BaseModel):
    """Output of the Forecasting Agent: predicted YoY performance under stress."""

    baseline_yoy_growth_pct: float
    stressed_yoy_growth_pct: float
    growth_delta_pct: float
    forecast_horizon_months: int
    monthly_projection: list[dict]  # [{month, baseline_revenue, stressed_revenue}, ...]
