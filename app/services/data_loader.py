"""
Data ingestion / validation service.

In the resume bullet, this replaces "legacy static ETL pipelines." Here's
the contrast that matters for an interview:

  Legacy static ETL:  a fixed, scheduled script that always runs the same
                       transform on the same source, regardless of context.

  This system:        the Data Ingestion Agent calls this service on-demand,
                       *as part of an agentic decision flow*, validates data
                       quality, and can short-circuit the whole graph (route
                       straight to an error report) if the data is bad --
                       something a static pipeline won't do gracefully.

This module itself only does plain, testable I/O + validation -- no LLM,
no LangGraph. Keeping it boring and deterministic is intentional.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.logging_config import logger
from app.models.domain import InventoryItem, Supplier


class DataValidationError(Exception):
    """Raised when ingested supply chain data fails schema/business validation."""


class SupplyChainDataLoader:
    """Loads and validates supplier + inventory data from JSON sources."""

    def __init__(self, data_dir: str | Path = "data/sample") -> None:
        self.data_dir = Path(data_dir)

    def load_suppliers(self) -> list[Supplier]:
        path = self.data_dir / "suppliers.json"
        raw = self._read_json(path)
        suppliers = [Supplier(**row) for row in raw]
        logger.info(f"Loaded {len(suppliers)} suppliers from {path}")
        return suppliers

    def load_inventory(self) -> list[InventoryItem]:
        path = self.data_dir / "inventory.json"
        raw = self._read_json(path)
        inventory = [InventoryItem(**row) for row in raw]
        logger.info(f"Loaded {len(inventory)} inventory items from {path}")
        return inventory

    def validate_referential_integrity(
        self, suppliers: list[Supplier], inventory: list[InventoryItem]
    ) -> tuple[bool, list[str]]:
        """
        Business-rule validation beyond simple schema checks: every
        inventory item must reference a supplier that actually exists.
        Static ETL pipelines often skip this and silently produce bad
        joins downstream -- here we catch it explicitly and report it.
        """
        problems: list[str] = []
        supplier_ids = {s.supplier_id for s in suppliers}

        for item in inventory:
            if item.primary_supplier_id not in supplier_ids:
                problems.append(
                    f"Inventory item '{item.sku}' references unknown supplier "
                    f"'{item.primary_supplier_id}'"
                )
            if item.current_stock_units < 0:
                problems.append(f"Inventory item '{item.sku}' has negative stock")

        is_valid = len(problems) == 0
        if not is_valid:
            logger.warning(f"Data validation found {len(problems)} issue(s): {problems}")
        else:
            logger.info("Data validation passed: referential integrity OK")

        return is_valid, problems

    @staticmethod
    def _read_json(path: Path) -> list[dict]:
        if not path.exists():
            raise DataValidationError(f"Required data file not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError as exc:
                raise DataValidationError(f"Malformed JSON in {path}: {exc}") from exc
