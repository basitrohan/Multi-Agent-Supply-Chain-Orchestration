#!/usr/bin/env python3
"""
Quick-start demo script: runs the full multi-agent stress-test workflow
directly (no need to start the FastAPI server first) and prints a clean
summary to the terminal.

Usage:
    python scripts/run_demo.py
    python scripts/run_demo.py --severity 0.9 --region APAC --days 30
    python scripts/run_demo.py --scenario "Critical Test" --disruption port_closure

This is the fastest way to see the whole system work end-to-end -- great
for a live interview demo where starting a server might feel slow or risky.
"""

import argparse
import sys
from pathlib import Path

# Make `app` importable when running this script directly from scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.domain import DisruptionType, StressTestRequest  # noqa: E402
from app.services.orchestration_service import run_stress_test  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a SupplyChain Sentinel stress-test demo.")
    parser.add_argument("--scenario", default="Demo Scenario - West Coast Port Closure")
    parser.add_argument(
        "--disruption",
        default="port_closure",
        choices=[d.value for d in DisruptionType],
    )
    parser.add_argument("--region", default="APAC")
    parser.add_argument("--severity", type=float, default=0.7)
    parser.add_argument("--days", type=int, default=21)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    request = StressTestRequest(
        scenario_name=args.scenario,
        disruption_type=DisruptionType(args.disruption),
        affected_region=args.region,
        severity=args.severity,
        duration_days=args.days,
    )

    print("=" * 70)
    print(f"Running stress test: {request.scenario_name}")
    print(f"  Disruption: {request.disruption_type.value} | Region: {request.affected_region}")
    print(f"  Severity: {request.severity:.0%} | Duration: {request.duration_days} days")
    print("=" * 70)
    print()

    result = run_stress_test(request)

    print()
    print("AGENT EXECUTION TRACE")
    print("-" * 70)
    for entry in result.audit_log:
        print(f"  [{entry['agent']:<18}] {entry['message']}")

    print()
    print("RESULTS SUMMARY")
    print("-" * 70)
    risk = result.risk_assessment
    sim = result.simulation_summary
    fc = result.forecast
    print(f"  Risk level:              {risk.get('risk_level')} (score {risk.get('risk_score')})")
    print(f"  Stockout probability:    {sim.get('stockout_probability', 0):.1%}")
    print(f"  Expected revenue impact: ${sim.get('expected_revenue_impact_usd', 0):,.0f}")
    print(f"  YoY growth impact:       {fc.get('growth_delta_pct', 0):+.2f} pts")

    print()
    if result.report_path:
        print(f"Full report saved to: {result.report_path}")
    if result.errors:
        print(f"Errors encountered: {result.errors}")
    print()


if __name__ == "__main__":
    main()
