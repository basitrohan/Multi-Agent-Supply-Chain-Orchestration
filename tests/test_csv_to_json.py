"""
Unit tests for the CSV conversion service (app/services/csv_converter_service.py)
and its thin CLI wrapper (scripts/csv_to_json.py).
"""

from pathlib import Path

import pytest

from app.services.csv_converter_service import (
    CsvConversionError,
    csv_file_to_records,
    csv_text_to_records,
)


def write_csv(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


class TestCsvTextToRecordsSuppliers:
    def test_converts_valid_csv_to_correct_types(self):
        csv_text = (
            "supplier_id,name,region,reliability_score,avg_lead_time_days,monthly_capacity_units\n"
            "SUP-1,Test Co,APAC,0.85,12,30000\n"
        )
        records = csv_text_to_records(csv_text, "suppliers")

        assert len(records) == 1
        record = records[0]
        assert record["supplier_id"] == "SUP-1"
        assert record["name"] == "Test Co"
        assert isinstance(record["reliability_score"], float)
        assert record["reliability_score"] == 0.85
        assert isinstance(record["avg_lead_time_days"], int)
        assert record["avg_lead_time_days"] == 12

    def test_handles_multiple_rows(self):
        csv_text = (
            "supplier_id,name,region,reliability_score,avg_lead_time_days,monthly_capacity_units\n"
            "SUP-1,A,APAC,0.8,10,1000\n"
            "SUP-2,B,EU,0.9,5,2000\n"
        )
        records = csv_text_to_records(csv_text, "suppliers")
        assert len(records) == 2
        assert records[1]["supplier_id"] == "SUP-2"

    def test_missing_required_column_raises_clear_error(self):
        csv_text = "supplier_id,name,reliability_score\nSUP-1,Test,0.8\n"
        with pytest.raises(CsvConversionError, match="missing required column"):
            csv_text_to_records(csv_text, "suppliers")

    def test_invalid_number_raises_clear_error_with_row_number(self):
        csv_text = (
            "supplier_id,name,region,reliability_score,avg_lead_time_days,monthly_capacity_units\n"
            "SUP-1,Test,APAC,not_a_number,10,1000\n"
        )
        with pytest.raises(CsvConversionError, match="Row 2"):
            csv_text_to_records(csv_text, "suppliers")

    def test_empty_data_raises_error(self):
        csv_text = "supplier_id,name,region,reliability_score,avg_lead_time_days,monthly_capacity_units\n"
        with pytest.raises(CsvConversionError, match="no data rows"):
            csv_text_to_records(csv_text, "suppliers")

    def test_unknown_entity_type_raises_error(self):
        with pytest.raises(CsvConversionError, match="Unknown entity_type"):
            csv_text_to_records("a,b\n1,2\n", "not_a_real_type")


class TestCsvTextToRecordsInventory:
    def test_converts_valid_inventory_csv(self):
        csv_text = (
            "sku,description,current_stock_units,reorder_point_units,"
            "avg_monthly_demand_units,unit_cost_usd,primary_supplier_id\n"
            "SKU-1,Widget,1000,200,500,4.5,SUP-1\n"
        )
        records = csv_text_to_records(csv_text, "inventory")

        assert len(records) == 1
        record = records[0]
        assert record["sku"] == "SKU-1"
        assert isinstance(record["unit_cost_usd"], float)
        assert isinstance(record["current_stock_units"], int)
        assert record["primary_supplier_id"] == "SUP-1"

    def test_tolerates_float_looking_integer_cells(self):
        """A cell like '1000.0' (common from Excel exports) should still convert to int."""
        csv_text = (
            "sku,description,current_stock_units,reorder_point_units,"
            "avg_monthly_demand_units,unit_cost_usd,primary_supplier_id\n"
            "SKU-1,Widget,1000.0,200.0,500.0,4.5,SUP-1\n"
        )
        records = csv_text_to_records(csv_text, "inventory")
        assert records[0]["current_stock_units"] == 1000
        assert isinstance(records[0]["current_stock_units"], int)


class TestCsvFileToRecords:
    def test_reads_and_converts_a_real_file(self, tmp_path):
        csv_path = write_csv(
            tmp_path,
            "suppliers.csv",
            "supplier_id,name,region,reliability_score,avg_lead_time_days,monthly_capacity_units\n"
            "SUP-1,Test Co,APAC,0.85,12,30000\n",
        )
        records = csv_file_to_records(csv_path, "suppliers")
        assert len(records) == 1
        assert records[0]["supplier_id"] == "SUP-1"

    def test_missing_file_raises_clear_error(self, tmp_path):
        missing_path = tmp_path / "does_not_exist.csv"
        with pytest.raises(CsvConversionError, match="File not found"):
            csv_file_to_records(missing_path, "suppliers")
