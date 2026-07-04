#!/usr/bin/env python3
"""
CSV -> JSON converter for SupplyChain Sentinel data files (command-line).

WHAT THIS DOES
---------------
The project reads supplier and inventory data from JSON files
(data/sample/suppliers.json and inventory.json). Most real-world data
(exports from Excel, an ERP system, etc.) comes as CSV instead. This
script converts a CSV file into the exact JSON structure the project
expects -- so you don't have to manually retype anything.

The actual conversion/validation logic lives in
app/services/csv_converter_service.py, since the same logic is also used
by the API's CSV upload endpoint (POST /api/v1/data/upload). This script
is a thin command-line wrapper around that shared service.

HOW TO USE IT
--------------
1. Fill in a CSV file using the templates in data/csv_templates/
   (suppliers_template.csv or inventory_template.csv) -- keep the same
   column headers, just change the values / add more rows.

2. Run one of:

   python scripts/csv_to_json.py suppliers path/to/your_suppliers.csv
   python scripts/csv_to_json.py inventory path/to/your_inventory.csv

3. This writes the result to data/sample/suppliers.json or
   inventory.json, replacing the demo data -- the rest of the project
   (the demo script, the API, the agents) then automatically uses your
   new data, with no other changes needed.

   Add --output some/other/path.json to write somewhere else instead
   of overwriting the live sample data.
"""

import argparse
import json
import sys
from pathlib import Path

# Make `app` importable when running this script directly from scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.csv_converter_service import CsvConversionError, csv_file_to_records  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a suppliers or inventory CSV file into the project's JSON format."
    )
    parser.add_argument("entity_type", choices=["suppliers", "inventory"], help="Which kind of data this is.")
    parser.add_argument("csv_path", type=Path, help="Path to your CSV file.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Where to save the JSON. Defaults to data/sample/<entity_type>.json (overwrites the demo data).",
    )
    args = parser.parse_args()

    output_path = args.output or Path("data/sample") / f"{args.entity_type}.json"

    try:
        records = csv_file_to_records(args.csv_path, args.entity_type)
    except CsvConversionError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    print(f"Converted {len(records)} {args.entity_type} record(s) from '{args.csv_path}'")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()
