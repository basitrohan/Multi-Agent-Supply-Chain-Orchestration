"""
FastAPI route definitions.

This is the "Implemented FastAPI microservices to trigger agentic
workflows" part of the resume bullet, made concrete:

    POST /api/v1/stress-test     -> triggers the full LangGraph agent workflow
    GET  /api/v1/reports/{id}    -> fetch a previously generated report
    GET  /api/v1/reports         -> list previously generated reports
    GET  /api/v1/data/summary    -> what supplier/inventory data is currently loaded
    POST /api/v1/data/upload     -> upload a CSV to replace the supplier/inventory data
    GET  /api/v1/health          -> service health + which LLM backend is active

Route handlers are deliberately thin: parse/validate input (FastAPI +
Pydantic do this automatically), delegate to the orchestration service,
shape the response. No business logic lives here.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.schemas import (
    CsvUploadResponse,
    DataSummaryResponse,
    HealthResponse,
    StressTestRequest,
    StressTestResponse,
)
from app.core.config import get_settings
from app.core.logging_config import logger
from app.services.csv_converter_service import CsvConversionError, csv_text_to_records
from app.services.orchestration_service import run_stress_test

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check() -> HealthResponse:
    """Simple liveness/readiness probe, also reports which LLM backend is active."""
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version="1.0.0",
        bedrock_mode="live" if (settings.bedrock_available and not settings.use_mock_llm) else "mock",
    )


@router.post("/stress-test", response_model=StressTestResponse, tags=["Stress Test"])
def trigger_stress_test(request: StressTestRequest) -> StressTestResponse:
    """
    Trigger the full multi-agent supply chain stress-test workflow.

    This single endpoint kicks off the entire LangGraph run: data
    ingestion -> risk assessment -> Monte Carlo simulation (with
    automatic retry/escalation on high risk) -> YoY forecasting ->
    AWS Bedrock (or mock) report generation.
    """
    logger.info(f"Received stress-test request: {request.scenario_name}")

    try:
        result = run_stress_test(request)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unhandled error while running stress-test workflow")
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {exc}") from exc

    if result.errors and not result.report_markdown:
        # Data validation failed upstream -- return a 422 with the specific problems
        # instead of a generic 500, since this is a client-data issue, not a server bug.
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Stress-test workflow halted due to data validation errors.",
                "errors": result.errors,
            },
        )

    return StressTestResponse(
        run_id=result.run_id,
        success=bool(result.report_markdown),
        risk_assessment=result.risk_assessment,
        simulation_summary=result.simulation_summary,
        forecast=result.forecast,
        report_markdown=result.report_markdown,
        report_path=result.report_path,
        audit_log=result.audit_log,
        errors=result.errors,
    )


@router.get("/reports/{scenario_slug}", tags=["Reports"])
def get_report(scenario_slug: str) -> dict:
    """Fetch a previously generated markdown report by its scenario slug."""
    report_path = Path(settings.reports_dir) / f"{scenario_slug}.md"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"No report found for '{scenario_slug}'")

    return {
        "scenario_slug": scenario_slug,
        "report_markdown": report_path.read_text(encoding="utf-8"),
    }


@router.get("/reports", tags=["Reports"])
def list_reports() -> dict:
    """List all generated report slugs available on disk."""
    reports_dir = Path(settings.reports_dir)
    if not reports_dir.exists():
        return {"reports": []}

    slugs = [p.stem for p in reports_dir.glob("*.md")]
    return {"reports": slugs}


@router.get("/data/summary", response_model=DataSummaryResponse, tags=["Data"])
def get_data_summary() -> DataSummaryResponse:
    """
    Return the supplier/inventory data currently loaded from data/sample/.

    This lets a UI show "here is the data a stress test will run against"
    without needing to know anything about the underlying JSON file layout
    -- useful right after a CSV upload, to confirm the new data took effect.
    """
    suppliers_path = Path(settings.sample_data_dir) / "suppliers.json"
    inventory_path = Path(settings.sample_data_dir) / "inventory.json"

    suppliers = json.loads(suppliers_path.read_text(encoding="utf-8")) if suppliers_path.exists() else []
    inventory = json.loads(inventory_path.read_text(encoding="utf-8")) if inventory_path.exists() else []

    regions = sorted({s["region"] for s in suppliers})

    return DataSummaryResponse(
        supplier_count=len(suppliers),
        inventory_count=len(inventory),
        regions=regions,
        suppliers=suppliers,
        inventory=inventory,
    )


@router.post("/data/upload", response_model=CsvUploadResponse, tags=["Data"])
async def upload_data_csv(
    entity_type: str,
    file: UploadFile = File(...),
) -> CsvUploadResponse:
    """
    Upload a CSV file to replace the current supplier or inventory data.

    `entity_type` must be "suppliers" or "inventory". The CSV is validated
    and converted using the same logic as scripts/csv_to_json.py (see
    app/services/csv_converter_service.py) -- a malformed file is rejected
    with a clear error naming the exact row/column at fault, instead of
    silently corrupting the live demo data.
    """
    if entity_type not in {"suppliers", "inventory"}:
        raise HTTPException(status_code=400, detail="entity_type must be 'suppliers' or 'inventory'.")

    raw_bytes = await file.read()
    try:
        csv_text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400, detail="File could not be read as text. Please upload a CSV file."
        )

    try:
        records = csv_text_to_records(csv_text, entity_type, source_label=file.filename or "uploaded file")
    except CsvConversionError as exc:
        logger.warning(f"CSV upload rejected for entity_type='{entity_type}': {exc}")
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    output_path = Path(settings.sample_data_dir) / f"{entity_type}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    logger.info(
        f"Replaced {entity_type} data via CSV upload: {len(records)} record(s) from '{file.filename}'"
    )

    return CsvUploadResponse(
        entity_type=entity_type,
        records_loaded=len(records),
        message=f"Loaded {len(records)} {entity_type} record(s) successfully.",
    )
