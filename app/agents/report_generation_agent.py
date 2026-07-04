"""
Report Generation Agent.

ROLE IN THE GRAPH: final node. Takes everything every previous agent
produced (risk assessment, simulation summary, YoY forecast) and asks an
LLM (AWS Bedrock, or the offline mock -- see app/services/llm_service.py)
to write it up as a polished markdown business report. This is the agent
that directly implements the resume bullet's "generating predictive YoY
performance reports via AWS Bedrock."

DESIGN NOTE: we don't let the LLM invent numbers. All figures (risk score,
stockout probability, revenue impact, YoY growth) are computed
deterministically by earlier agents and handed to the LLM as a structured
JSON block inside the prompt -- the LLM's job is ONLY to narrate and
contextualize them in natural language. This is a standard, important
guardrail for any "AI generates a business report" feature: numbers come
from code, narrative comes from the model.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.agents.agent_utils import log_step
from app.core.config import get_settings
from app.core.logging_config import logger
from app.models.state import GraphState
from app.services.llm_service import get_llm_client

settings = get_settings()

SYSTEM_PROMPT = """You are a supply chain risk analyst writing an executive report.
You will be given structured JSON data containing a risk assessment, Monte Carlo
stress-test simulation results, and a year-over-year (YoY) financial forecast.

Write a clear, professional markdown report for a VP of Operations audience.
Rules:
- Do NOT invent, alter, or round any numbers differently than given. Use the exact
  figures from the JSON.
- Structure the report with: Executive Summary, Risk Assessment, Simulation Results,
  YoY Forecast, and Recommended Actions.
- Keep the tone confident and action-oriented, not alarmist.
- Output ONLY the markdown report, no preamble.
"""


def _build_user_prompt(state: GraphState) -> str:
    payload = {
        "request": state["request"] if isinstance(state["request"], dict) else state["request"].model_dump(),
        "risk_assessment": state.get("risk_assessment_result", {}),
        "simulation_summary": state.get("simulation_summary", {}),
        "forecast": state.get("forecast_result", {}),
    }
    return (
        "Here is the structured stress-test data. Write the executive report now.\n\n"
        f"```json\n{json.dumps(payload, indent=2)}\n```"
    )


def report_generation_node(state: GraphState) -> dict:
    logger.info("[ReportGenerationAgent] Generating final report...")

    llm = get_llm_client()
    user_prompt = _build_user_prompt(state)
    report_markdown = llm.invoke(SYSTEM_PROMPT, user_prompt)

    request = state["request"] if isinstance(state["request"], dict) else state["request"].model_dump()
    scenario_slug = request.get("scenario_name", "report").lower().replace(" ", "_").replace("/", "-")

    reports_dir = Path(settings.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{scenario_slug}.md"
    report_path.write_text(report_markdown, encoding="utf-8")

    logger.info(f"[ReportGenerationAgent] Report written to {report_path}")

    return {
        "report_markdown": report_markdown,
        "report_path": str(report_path),
        "audit_log": log_step("report_generation", f"Report generated and saved to {report_path}."),
        "next_agent": "end",
    }
