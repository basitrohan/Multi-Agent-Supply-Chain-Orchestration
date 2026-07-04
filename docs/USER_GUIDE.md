# User Guide

This guide walks through running, using, and demoing the project — written in plain, simple language so you can follow it quickly even if it's the first time you're touching this exact codebase.

## Table of contents

1. [What you need installed](#what-you-need-installed)
2. [Option A: Run it locally (recommended for now)](#option-a-run-it-locally-recommended-for-now)
3. [Option B: Run it with Docker (for later, when you want to learn it)](#option-b-run-it-with-docker-for-later-when-you-want-to-learn-it)
4. [The fastest way to see it work: the demo script](#the-fastest-way-to-see-it-work-the-demo-script)
5. [Using the full API](#using-the-full-api)
6. [Using the web console (no terminal needed, after setup)](#using-the-web-console-no-terminal-needed-after-setup)
7. [Reading the generated report](#reading-the-generated-report)
8. [Using your own data (CSV instead of the sample JSON)](#using-your-own-data-csv-instead-of-the-sample-json)
9. [Connecting a real AWS Bedrock account (optional)](#connecting-a-real-aws-bedrock-account-optional)
10. [Running the tests](#running-the-tests)
11. [Common problems and fixes](#common-problems-and-fixes)

---

## What you need installed

- Python 3.11 or 3.12
- pip (comes with Python)
- (Optional, for later) Docker Desktop, if you want to try the containerized version

You do **not** need an AWS account. The project runs completely offline by default.

---

## Option A: Run it locally (recommended for now)

Open a terminal in the project folder and run these commands one at a time.

```bash
# Step 1: Create an isolated Python environment just for this project.
# This keeps its dependencies separate from anything else on your machine.
python3 -m venv venv

# Step 2: "Activate" that environment (you'll need to do this every time
# you open a new terminal to work on this project).
source venv/bin/activate
# On Windows, instead use: venv\Scripts\activate

# Step 3: Install everything the project needs to run.
pip install -r requirements.txt

# Step 3b (optional): also install testing/linting tools, if you want to run
# the test suite or contribute changes.
pip install -r requirements-dev.txt

# Step 4: Create your local settings file from the template.
# The defaults already work with no changes needed.
cp .env.example .env
```

That's the whole setup. Now you can either run the quick demo script, or start the full web server — see below.

**Tip:** every command in this guide also has a short version in the `Makefile` — run `make help` to see them all (e.g. `make install-dev`, `make demo`, `make run`, `make test`).

---

## Option B: Run it with Docker (for later, when you want to learn it)

Docker packages the whole application — Python, all dependencies, your code — into one self-contained "container" that runs the same way on any machine. Here is the plain-language version of what's happening and how to actually do it once you have Docker Desktop installed.

### What the two Docker files do

- **`Dockerfile`** — a recipe that says "start from a clean Python image, install our dependencies, copy in our code, and here's the command to start the server." It uses a "multi-stage build," which just means: use one temporary stage to install/compile everything, then copy *only the finished result* into a clean, smaller final image. This keeps the final container small and avoids leaving build tools lying around in production.
- **`docker-compose.yml`** — a short file that says "run the container described by the Dockerfile, and here's exactly how": which port to expose, which environment file to load, where to save generated reports on your actual computer so they don't disappear when the container stops.

### How to actually run it

```bash
# Build the image and start the container, all in one command.
docker compose up --build

# Now open http://localhost:8000/docs in your browser.

# When you're done, stop everything with:
docker compose down
```

That's genuinely it. Docker Compose reads `docker-compose.yml`, which tells it to build from the `Dockerfile`, and the result is identical to running it locally — except now it's running inside an isolated container instead of directly on your machine.

### A few things worth understanding (for when you study this further)

- `docker compose up --build` rebuilds the image if you've changed any code. If you only changed `.env` values, you can usually skip `--build`.
- Generated reports are saved to `./data/reports` on your real computer (not lost inside the container) because of this line in `docker-compose.yml`:
  ```yaml
  volumes:
    - ./data/reports:/app/data/reports
  ```
  This is called a "volume mount" — it connects a folder inside the container to a folder on your actual machine, so the two stay in sync.
- The container runs as a non-root user (`appuser`), which is a standard security practice — if anything malicious ever got into the container, it wouldn't have full administrator rights inside it.

---

## The fastest way to see it work: the demo script

If you just want to see the whole multi-agent system run, without starting a web server at all, use this:

```bash
python scripts/run_demo.py
```

This runs one full stress-test scenario directly in your terminal and prints:
- A trace of which agent ran and what it decided, in order
- The final risk score, simulation results, and forecast numbers
- Where the generated report was saved

You can customize the scenario with command-line flags:

```bash
python scripts/run_demo.py --scenario "Critical Test" --disruption port_closure --region APAC --severity 0.95 --days 45
```

Try a high severity value (like `0.95`) and a long duration (like `45` days) — you'll see in the printed trace that the Simulation agent runs more than once, because the system decided the first result wasn't trustworthy enough and re-ran itself with more iterations. That's the key "agentic" behavior worth pointing out if you're demoing this live.

---

## Using the full API

To use the actual web service (the way a real client application would), start the server:

```bash
uvicorn app.main:app --reload
```

Then open your browser to **http://localhost:8000/docs** — this is an automatically generated, interactive page (called "Swagger UI") where you can try every endpoint by clicking buttons, no command-line tools needed.

### Calling it with curl, if you prefer the terminal

```bash
curl -X POST http://localhost:8000/api/v1/stress-test \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_name": "APAC Port Closure",
    "disruption_type": "port_closure",
    "affected_region": "APAC",
    "severity": 0.8,
    "duration_days": 21
  }'
```

Valid `disruption_type` values: `supplier_delay`, `demand_spike`, `port_closure`, `raw_material_shortage`, `logistics_disruption`.

`severity` must be a number between `0.0` (barely noticeable) and `1.0` (catastrophic).

### Checking which mode the system is running in

```bash
curl http://localhost:8000/api/v1/health
```

This tells you whether the system is using a real AWS Bedrock connection (`"bedrock_mode": "live"`) or the offline mock (`"bedrock_mode": "mock"`).

### Listing and fetching past reports

```bash
curl http://localhost:8000/api/v1/reports
curl http://localhost:8000/api/v1/reports/apac_port_closure
```

---

## Using the web console (no terminal needed, after setup)

If typing API requests isn't your thing, there's a browser-based interface that does all of the above with forms and buttons instead.

**You still need the backend running** (see Option A above) — the web console is a separate small app that talks to it.

```bash
# Terminal 1 (leave running):
uvicorn app.main:app --reload

# Terminal 2:
cd frontend
npm install      # first time only
npm run dev
```

Open the address it prints, usually `http://localhost:5173`. From there you can:
- Fill in a scenario and click **Run stress test** — watch each of the five agents "stamp" through a live checklist as they complete.
- See the risk level, simulation results, and a 12-month forecast chart, without reading any JSON.
- Upload your own suppliers/inventory CSV file directly with a file picker — no command line needed (this uses the same CSV format described below, just through a web form instead of a script).

See `frontend/README.md` for more detail on the web console specifically.

---

## Reading the generated report

Every stress test saves a markdown report to `data/reports/<scenario-name>.md`. Open it in any text editor, or in VS Code / a markdown viewer for nicer formatting. It contains:

- An executive summary written in plain business language
- The computed risk score and level (LOW / MODERATE / HIGH / CRITICAL)
- The specific vulnerabilities found (which suppliers, which products)
- The Monte Carlo simulation results (stockout probability, expected and worst-case dollar impact)
- The year-over-year growth forecast with and without the disruption
- Recommended actions

---

## Using your own data (CSV instead of the sample JSON)

The project ships with made-up demo data (`data/sample/suppliers.json` and `inventory.json`). If you have real supplier/inventory data in a spreadsheet, you can convert it to the format this project needs without retyping anything by hand.

### Step 1: Fill in a CSV template

Open `data/csv_templates/suppliers_template.csv` and `data/csv_templates/inventory_template.csv` in Excel or Notepad. Keep the column headers exactly as they are — just replace the example row with your own rows (add as many as you like). See `data/csv_templates/README.md` for what each column means in plain language.

A couple of rules to avoid errors:
- Numbers must be plain numbers — write `50000`, not `$50,000`.
- Every `primary_supplier_id` in your inventory file must match a `supplier_id` that actually exists in your suppliers file.

### Step 2: Convert it

```bash
python scripts/csv_to_json.py suppliers data/csv_templates/suppliers_template.csv
python scripts/csv_to_json.py inventory data/csv_templates/inventory_template.csv
```

This overwrites `data/sample/suppliers.json` and `inventory.json` with your data — converted automatically into the exact format the project expects. If something in your CSV is wrong (a missing column, a number that isn't really a number), the script tells you exactly which row and column the problem is in, instead of crashing or silently breaking.

### Step 3: Run as normal

```bash
python scripts/run_demo.py
```

Nothing else changes — the same five agents, the same simulation, now running against your data instead of the demo data.

**To go back to the original demo data later**, just re-download the project or restore `suppliers.json`/`inventory.json` from a backup — the converter always overwrites those two files (unless you use `--output some/other/path.json`).

---

## Connecting a real AWS Bedrock account (optional)

You don't need this to use or demo the project. If you later want to connect a real AWS account:

1. Get AWS credentials with access to Bedrock (an access key ID and secret access key) from your AWS account.
2. Open `.env` and fill in:
   ```
   AWS_ACCESS_KEY_ID=your-key-here
   AWS_SECRET_ACCESS_KEY=your-secret-here
   USE_MOCK_LLM=false
   ```
3. Restart the server (or re-run the demo script). The exact same code now sends the report-writing request to the real Claude model on AWS Bedrock instead of using the offline template engine — nothing else changes.

If the real Bedrock call ever fails (wrong permissions, model not enabled in your AWS region, etc.), the system automatically falls back to the offline mock for that request and logs a warning, rather than crashing.

---

## Running the tests

```bash
pytest -v
```

This runs all 30 automated tests: the Monte Carlo simulation math, the data validation logic, each individual agent, the full multi-agent workflow end-to-end, and the API endpoints. All of them should pass without needing any AWS credentials.

---

## Common problems and fixes

**"command not found: python3" or "command not found: pip"**
Make sure Python is installed and on your system PATH. On Windows you may need to use `python` instead of `python3`.

**Dependency install fails with a version conflict**
This project pins compatible version ranges in `requirements.txt` specifically to avoid this — if you still hit one, run `pip install --upgrade pip` first, then retry.

**Port 8000 already in use**
Another program is using that port. Either stop it, or start uvicorn on a different port: `uvicorn app.main:app --reload --port 8001`.

**Reports folder is empty after running the demo**
Check the terminal output for the exact path it printed (it includes the scenario name, lowercased with underscores) — and make sure you're looking inside `data/reports/` relative to the project root, not somewhere else.

**Docker build is slow the first time**
This is normal — the first build downloads the Python base image and installs every dependency. Subsequent builds are much faster because Docker caches unchanged steps.
