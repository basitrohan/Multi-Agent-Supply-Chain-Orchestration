"""
CSV -> structured-record conversion service.

WHY THIS LIVES IN app/services/ AND NOT IN scripts/
-------------------------------------------------------
This logic is used in two places: the command-line converter
(scripts/csv_to_json.py) and the FastAPI upload endpoint
(POST /api/v1/data/upload). Anything used by both the CLI and the API
belongs in the service layer, not in a one-off script -- that's the same
layering principle the rest of this project follows (see
docs/ARCHITECTURE.md). The script becomes a thin wrapper around this.

WHAT IT DOES
-------------
Validates a CSV file's columns and value types against the schema for
either "suppliers" or "inventory" (kept in sync with the Pydantic models
in app/models/domain.py), and converts it into a list of plain dicts
ready to be written as JSON or fed directly into SupplyChainDataLoader.

Validation failures raise CsvConversionError with a message that names
the exact row and column at fault, rather than failing silently or
producing malformed data.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

# ----------------------------------------------------------------------
# Column definitions: maps each entity type to its required columns and
# the Python type each column must convert to. This MUST stay in sync
# with the Pydantic models in app/models/domain.py (Supplier, InventoryItem)
# -- if those models ever change, update this dictionary to match.
# ----------------------------------------------------------------------

SCHEMAS: dict[str, dict[str, type]] = {
    "suppliers": {
        "supplier_id": str,
        "name": str,
        "region": str,
        "reliability_score": float,
        "avg_lead_time_days": int,
        "monthly_capacity_units": int,
    },
    "inventory": {
        "sku": str,
        "description": str,
        "current_stock_units": int,
        "reorder_point_units": int,
        "avg_monthly_demand_units": int,
        "unit_cost_usd": float,
        "primary_supplier_id": str,
    },
}


class CsvConversionError(Exception):
    """Raised when a CSV file fails schema or type validation."""


def _convert_value(raw_value: str, target_type: type, column: str, row_number: int) -> object:
    """Convert one CSV cell to the correct Python type, with a clear error if it fails."""
    raw_value = raw_value.strip()
    try:
        if target_type is float:
            return float(raw_value)
        if target_type is int:
            return int(float(raw_value))  # tolerant of "50000.0" style cells
        return raw_value  # str: no conversion needed
    except ValueError:
        raise CsvConversionError(
            f"Row {row_number}, column '{column}': expected a {target_type.__name__}, got '{raw_value}'"
        ) from None


def csv_text_to_records(csv_text: str, entity_type: str, source_label: str = "uploaded file") -> list[dict]:
    """
    Convert raw CSV text (already read into memory) into a list of
    validated dicts. This is the core conversion used by both the file-path
    based `csv_file_to_records` (CLI) and the in-memory upload endpoint (API).
    """
    if entity_type not in SCHEMAS:
        raise CsvConversionError(f"Unknown entity_type '{entity_type}'. Must be 'suppliers' or 'inventory'.")

    schema = SCHEMAS[entity_type]
    required_columns = set(schema.keys())

    reader = csv.DictReader(io.StringIO(csv_text))

    if reader.fieldnames is None:
        raise CsvConversionError(f"'{source_label}' appears to be empty (no header row found).")

    actual_columns = set(reader.fieldnames)
    missing = required_columns - actual_columns
    if missing:
        raise CsvConversionError(
            f"'{source_label}' is missing required column(s): {sorted(missing)}\n"
            f"Required columns are: {sorted(required_columns)}\n"
            f"Found columns were:   {sorted(actual_columns)}"
        )

    records = []
    for row_number, row in enumerate(reader, start=2):  # row 1 is the header
        record = {}
        for column, target_type in schema.items():
            record[column] = _convert_value(row[column], target_type, column, row_number)
        records.append(record)

    if not records:
        raise CsvConversionError(f"'{source_label}' has a header row but no data rows.")

    return records


def csv_file_to_records(csv_path: Path, entity_type: str) -> list[dict]:
    """Read a CSV file from disk and convert it (used by the CLI script)."""
    if not csv_path.exists():
        raise CsvConversionError(f"File not found: {csv_path}")
    csv_text = csv_path.read_text(encoding="utf-8-sig")
    return csv_text_to_records(csv_text, entity_type, source_label=str(csv_path))
