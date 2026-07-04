# CSV Templates — Column Guide

Fill in these CSV files with your own real data, keeping the column headers exactly as they are. Then convert them to JSON using `scripts/csv_to_json.py` (see the main `docs/USER_GUIDE.md` or just run `python scripts/csv_to_json.py --help`).

## `suppliers_template.csv`

| Column | Meaning | Example |
|---|---|---|
| `supplier_id` | A unique code for this supplier — you make this up, just keep each one unique | `SUP-001` |
| `name` | The supplier's real name | `Acme Components Ltd.` |
| `region` | Where they're based (used to match against "affected region" in a scenario) | `APAC`, `North America`, `EU` |
| `reliability_score` | A number between 0 and 1 — how dependable they are (1 = perfectly reliable) | `0.85` |
| `avg_lead_time_days` | How many days they usually take to deliver | `18` |
| `monthly_capacity_units` | How many units they can supply per month | `50000` |

## `inventory_template.csv`

| Column | Meaning | Example |
|---|---|---|
| `sku` | A unique product code | `SKU-1001` |
| `description` | The product's name | `Lithium-Ion Battery Cell` |
| `current_stock_units` | How many units you currently have in stock | `42000` |
| `reorder_point_units` | The stock level at which you'd normally reorder | `15000` |
| `avg_monthly_demand_units` | How many units you typically sell/use per month | `28000` |
| `unit_cost_usd` | Cost per unit, in US dollars | `3.10` |
| `primary_supplier_id` | Must match a `supplier_id` from your suppliers CSV exactly | `SUP-001` |

## Important rules

- **Don't rename the column headers** — the converter looks for these exact names.
- **Numbers must be plain numbers** — no `$`, no commas (write `50000`, not `$50,000`).
- **`primary_supplier_id` in inventory must exist in your suppliers file** — if it doesn't match any `supplier_id`, the project's data validation step will reject it (on purpose — this is the same safety check described in `docs/ARCHITECTURE.md`).
- Add as many rows as you want — one supplier/product per row.
