"""
API request/response schemas.

These are separate from app/models/domain.py on purpose: domain models
describe business concepts, but API schemas describe the HTTP *contract*.
They often overlap heavily (as here) but keeping them distinct means we
can evolve the public API independently of internal domain modeling --
standard practice for any service that other teams might call.
"""

from pydantic import BaseModel

from app.models.domain import StressTestRequest


class StressTestResponse(BaseModel):
    """Response returned after a stress-test workflow completes."""

    run_id: str
    success: bool
    risk_assessment: dict
    simulation_summary: dict
    forecast: dict
    report_markdown: str | None = None
    report_path: str | None = None
    audit_log: list[dict]
    errors: list[str]


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    bedrock_mode: str  # "live" | "mock"


class CsvUploadResponse(BaseModel):
    """Response returned after uploading and converting a CSV file."""

    entity_type: str  # "suppliers" | "inventory"
    records_loaded: int
    message: str


class DataSummaryResponse(BaseModel):
    """A lightweight summary of the currently loaded supplier/inventory data,
    so a UI can show 'what data am I about to run a stress test against'
    without needing to know the internal JSON file structure."""

    supplier_count: int
    inventory_count: int
    regions: list[str]
    suppliers: list[dict]
    inventory: list[dict]


# Re-export so route files have one import location.
__all__ = [
    "StressTestRequest",
    "StressTestResponse",
    "HealthResponse",
    "CsvUploadResponse",
    "DataSummaryResponse",
]
