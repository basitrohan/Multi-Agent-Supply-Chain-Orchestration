"""
Shared helper utilities used by every agent node.

Keeping this tiny and dependency-free on purpose: agents import `log_step`
to append a consistent, timestamped entry to the shared audit trail
(GraphState.audit_log) every time they run. This gives us a full,
human-readable record of *what the multi-agent system actually decided*
at each step -- which is exactly what you'd want to show an interviewer
(or a real compliance/ops team) as proof the system isn't a black box.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.state import AgentLogEntry, AgentName


def log_step(agent: AgentName, message: str) -> list[AgentLogEntry]:
    """
    Build a single audit-log entry as a list (LangGraph state field uses
    operator.add to merge lists across nodes, so every agent returns a
    one-item list rather than appending to a list it doesn't own).
    """
    entry: AgentLogEntry = {
        "agent": agent,
        "message": message,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    return [entry]
