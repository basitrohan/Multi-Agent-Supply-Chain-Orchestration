"""Unit tests for the supply chain data loader and validation logic."""

import pytest

from app.models.domain import InventoryItem, Supplier
from app.services.data_loader import DataValidationError, SupplyChainDataLoader


class TestSupplyChainDataLoader:
    def test_load_suppliers_from_sample_data(self):
        loader = SupplyChainDataLoader(data_dir="data/sample")
        suppliers = loader.load_suppliers()

        assert len(suppliers) > 0
        assert all(isinstance(s, Supplier) for s in suppliers)

    def test_load_inventory_from_sample_data(self):
        loader = SupplyChainDataLoader(data_dir="data/sample")
        inventory = loader.load_inventory()

        assert len(inventory) > 0
        assert all(isinstance(i, InventoryItem) for i in inventory)

    def test_missing_file_raises_validation_error(self, tmp_path):
        loader = SupplyChainDataLoader(data_dir=tmp_path)
        with pytest.raises(DataValidationError):
            loader.load_suppliers()

    def test_malformed_json_raises_validation_error(self, tmp_path):
        bad_file = tmp_path / "suppliers.json"
        bad_file.write_text("{not valid json,,,")
        loader = SupplyChainDataLoader(data_dir=tmp_path)
        with pytest.raises(DataValidationError):
            loader.load_suppliers()

    def test_referential_integrity_passes_for_valid_data(self, sample_suppliers, sample_inventory):
        loader = SupplyChainDataLoader()
        suppliers = [Supplier(**s) for s in sample_suppliers]
        inventory = [InventoryItem(**i) for i in sample_inventory]

        is_valid, problems = loader.validate_referential_integrity(suppliers, inventory)

        assert is_valid is True
        assert problems == []

    def test_referential_integrity_fails_for_unknown_supplier(self, sample_suppliers, sample_inventory):
        loader = SupplyChainDataLoader()
        suppliers = [Supplier(**s) for s in sample_suppliers]

        sample_inventory[0]["primary_supplier_id"] = "SUP-GHOST"
        inventory = [InventoryItem(**i) for i in sample_inventory]

        is_valid, problems = loader.validate_referential_integrity(suppliers, inventory)

        assert is_valid is False
        assert len(problems) == 1
        assert "SUP-GHOST" in problems[0]
