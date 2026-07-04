"""
LLM service layer: AWS Bedrock client with automatic mock fallback.

WHY THIS FILE EXISTS
---------------------
The Report Generation Agent needs to call a large language model to turn
structured numbers (risk scores, simulation stats, forecasts) into a
readable business report. In production that LLM call goes to AWS Bedrock
(Anthropic Claude models hosted on AWS).

But not everyone running this project has AWS credentials configured --
and an interviewer reading this code shouldn't need them either. So this
module defines one interface (`LLMClient.invoke`) with two implementations:

    BedrockLLMClient  -> real call to AWS Bedrock (boto3 bedrock-runtime)
    MockLLMClient     -> deterministic, template-based "fake" response

`get_llm_client()` picks the right one automatically based on whether AWS
credentials are present (see app/core/config.py: `bedrock_available`).
This is the Strategy design pattern, and it's exactly how you'd want to
structure this in a real production system anyway -- LLM providers change,
and business logic should never know which one it's talking to.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from app.core.config import get_settings
from app.core.logging_config import logger

settings = get_settings()


class LLMClient(ABC):
    """Common interface every LLM backend must implement."""

    @abstractmethod
    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        """Send a prompt to the model and return its text response."""
        raise NotImplementedError


class BedrockLLMClient(LLMClient):
    """
    Real AWS Bedrock client.

    Uses the bedrock-runtime `converse` API, which is Anthropic + AWS's
    recommended unified interface across all Bedrock model families (it
    normalizes the request/response shape regardless of underlying model).
    """

    def __init__(self) -> None:
        import boto3  # local import keeps boto3 optional when running mock-only

        self._client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        logger.info(
            f"BedrockLLMClient initialized | model={settings.bedrock_model_id} | region={settings.aws_region}"
        )

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.converse(
                modelId=settings.bedrock_model_id,
                system=[{"text": system_prompt}],
                messages=[{"role": "user", "content": [{"text": user_prompt}]}],
                inferenceConfig={
                    "maxTokens": settings.bedrock_max_tokens,
                    "temperature": settings.bedrock_temperature,
                },
            )
            return response["output"]["message"]["content"][0]["text"]
        except Exception as exc:  # noqa: BLE001 - we want to fail soft and log
            logger.error(f"Bedrock invocation failed: {exc}. Falling back to mock output for this call.")
            return MockLLMClient().invoke(system_prompt, user_prompt)


class MockLLMClient(LLMClient):
    """
    Deterministic offline stand-in for Bedrock.

    This is NOT just a stub that returns "lorem ipsum" -- it actually reads
    the structured numbers out of the prompt (we pass them as a JSON block,
    see ReportGenerationAgent) and renders a real, sensible markdown report
    using string templates. This means the *entire project runs end-to-end
    and produces a genuinely readable report* with zero AWS dependency,
    which matters a lot when demoing this without cloud credentials.
    """

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        logger.info("MockLLMClient invoked (no AWS credentials configured - using offline template engine)")

        payload = self._extract_json_block(user_prompt)
        if payload is None:
            return (
                "## Report\n\n_Mock LLM: no structured data block found in prompt; "
                "returning placeholder narrative._"
            )
        return self._render_report(payload)

    @staticmethod
    def _extract_json_block(prompt: str) -> dict[str, Any] | None:
        start = prompt.find("```json")
        end = prompt.find("```", start + 7)
        if start == -1 or end == -1:
            return None
        try:
            return json.loads(prompt[start + 7 : end].strip())
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _render_report(data: dict[str, Any]) -> str:
        req = data.get("request", {})
        risk = data.get("risk_assessment", {})
        sim = data.get("simulation_summary", {})
        fc = data.get("forecast", {})

        risk_level = risk.get("risk_level", "UNKNOWN")
        risk_score = risk.get("risk_score", 0)
        vulnerabilities = risk.get("key_vulnerabilities", [])

        stockout_prob = sim.get("stockout_probability", 0) * 100
        expected_impact = sim.get("expected_revenue_impact_usd", 0)
        p90_impact = sim.get("p90_revenue_impact_usd", 0)
        worst_case = sim.get("worst_case_revenue_impact_usd", 0)
        recovery_days = sim.get("avg_recovery_time_days", 0)

        baseline_growth = fc.get("baseline_yoy_growth_pct", 0)
        stressed_growth = fc.get("stressed_yoy_growth_pct", 0)
        delta = fc.get("growth_delta_pct", 0)

        vuln_lines = "\n".join(f"- {v}" for v in vulnerabilities) or "- None identified"

        narrative = MockLLMClient._risk_narrative(risk_level, stockout_prob, delta)

        return f"""# Supply Chain Stress Test Report

## Scenario: {req.get('scenario_name', 'Unnamed Scenario')}

**Disruption type:** {req.get('disruption_type', 'n/a')}
**Affected region:** {req.get('affected_region', 'n/a')}
**Severity:** {req.get('severity', 0):.0%}
**Duration:** {req.get('duration_days', 'n/a')} days

---

## Executive Summary

{narrative}

---

## Risk Assessment

| Metric | Value |
|---|---|
| Risk Score | {risk_score:.2f} / 1.00 |
| Risk Level | **{risk_level}** |

**Key vulnerabilities identified:**
{vuln_lines}

---

## Stress Test Simulation Results

Simulation was run across {sim.get('total_runs', 'N/A')} Monte Carlo iterations.

| Metric | Value |
|---|---|
| Stockout Probability | {stockout_prob:.1f}% |
| Expected Revenue Impact | ${expected_impact:,.0f} |
| P90 Revenue Impact (worse-case tail) | ${p90_impact:,.0f} |
| Absolute Worst Case | ${worst_case:,.0f} |
| Avg. Recovery Time | {recovery_days:.1f} days |

---

## Year-over-Year Predictive Performance

| Metric | Value |
|---|---|
| Baseline YoY Growth (no disruption) | {baseline_growth:+.1f}% |
| Stressed YoY Growth (with disruption) | {stressed_growth:+.1f}% |
| Growth Impact | {delta:+.1f} pts |

---

## Recommended Actions

{MockLLMClient._recommendations(risk_level)}

---
*Report generated by SupplyChain Sentinel — automated multi-agent stress-test pipeline.*
*Narrative generated by: Offline Mock LLM (AWS Bedrock not configured for this run).*
"""

    @staticmethod
    def _risk_narrative(risk_level: str, stockout_prob: float, delta: float) -> str:
        if risk_level == "CRITICAL":
            return (
                f"This scenario presents a **CRITICAL** risk to supply chain continuity, with a "
                f"{stockout_prob:.0f}% probability of stockout events and a projected YoY growth "
                f"impact of {delta:+.1f} percentage points. Immediate mitigation is recommended."
            )
        if risk_level == "HIGH":
            return (
                f"This scenario presents a **HIGH** risk profile, with a {stockout_prob:.0f}% chance of "
                f"stockouts and an estimated {delta:+.1f} point swing in YoY growth. Proactive supplier "
                f"diversification is advised."
            )
        if risk_level == "MODERATE":
            return (
                f"This scenario presents a **MODERATE** risk level. Stockout probability stands at "
                f"{stockout_prob:.0f}%, with a manageable {delta:+.1f} point YoY growth impact. "
                f"Standard contingency buffers should suffice."
            )
        return (
            f"This scenario presents a **LOW** risk level, with minimal disruption expected "
            f"({stockout_prob:.0f}% stockout probability, {delta:+.1f} pt YoY impact). "
            f"Existing safety stock levels appear adequate."
        )

    @staticmethod
    def _recommendations(risk_level: str) -> str:
        base = [
            "Increase safety stock for SKUs sourced from the affected region.",
            "Activate secondary/backup suppliers where available.",
            "Monitor lead times daily for the duration of the disruption window.",
        ]
        if risk_level in ("HIGH", "CRITICAL"):
            base.insert(0, "Convene a cross-functional incident response team within 24 hours.")
            base.append(
                "Consider air-freight or expedited logistics for highest-priority SKUs despite added cost."
            )
        return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(base))


def get_llm_client() -> LLMClient:
    """
    Factory function: returns a real Bedrock client if AWS credentials are
    configured, otherwise returns the offline MockLLMClient.

    This single function is the ONLY place in the codebase that decides
    "real vs mock" -- every agent just calls get_llm_client().invoke(...)
    and doesn't need to know or care which one it got.
    """
    if settings.bedrock_available and not settings.use_mock_llm:
        try:
            return BedrockLLMClient()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Failed to initialize Bedrock client ({exc}); falling back to MockLLMClient.")
            return MockLLMClient()

    logger.info("No AWS Bedrock credentials detected -> using MockLLMClient (offline mode).")
    return MockLLMClient()
