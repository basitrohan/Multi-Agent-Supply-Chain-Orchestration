const AGENT_LABELS = {
  data_ingestion: { name: "Data Ingestion", code: "01" },
  risk_assessment: { name: "Risk Assessment", code: "02" },
  simulation: { name: "Simulation", code: "03" },
  forecasting: { name: "Forecasting", code: "04" },
  report_generation: { name: "Report Generation", code: "05" },
};

const PIPELINE_ORDER = [
  "data_ingestion",
  "risk_assessment",
  "simulation",
  "forecasting",
  "report_generation",
];

/**
 * The signature visual for the product: each agent in the LangGraph
 * pipeline "stamps" a checkpoint as it completes, like a manifest moving
 * through customs/inspection points. A retried simulation step shows a
 * doubled stamp -- making the agentic retry/escalation loop visible at a
 * glance, which is the one thing about this product that isn't generic.
 */
export default function AgentManifest({ auditLog, status }) {
  // Group log entries by agent so retries (multiple simulation entries)
  // render as stacked stamps under the same checkpoint.
  const entriesByAgent = {};
  for (const entry of auditLog || []) {
    if (!entriesByAgent[entry.agent]) entriesByAgent[entry.agent] = [];
    entriesByAgent[entry.agent].push(entry);
  }

  return (
    <div className="manifest">
      <div className="manifest-header">
        <span className="manifest-eyebrow">Agent pipeline</span>
        <span className="manifest-status">
          {status === "running" ? "In progress" : status === "done" ? "Complete" : "Idle"}
        </span>
      </div>

      <div className="manifest-rail">
        {PIPELINE_ORDER.map((agentKey, idx) => {
          const entries = entriesByAgent[agentKey] || [];
          const isStamped = entries.length > 0;
          const isRetried = entries.length > 1;
          const isActive =
            status === "running" &&
            !isStamped &&
            PIPELINE_ORDER.slice(0, idx).every((k) => entriesByAgent[k]?.length > 0);

          return (
            <div className="manifest-row" key={agentKey}>
              <div className="manifest-track">
                <div
                  className={`manifest-node ${isStamped ? "is-stamped" : ""} ${
                    isActive ? "is-active" : ""
                  }`}
                >
                  {isStamped ? "✓" : AGENT_LABELS[agentKey].code}
                </div>
                {idx < PIPELINE_ORDER.length - 1 && (
                  <div className={`manifest-connector ${isStamped ? "is-filled" : ""}`} />
                )}
              </div>

              <div className="manifest-content">
                <div className="manifest-title-row">
                  <span className="manifest-title">{AGENT_LABELS[agentKey].name}</span>
                  {isRetried && (
                    <span className="manifest-retry-tag">
                      re-run &times;{entries.length}
                    </span>
                  )}
                </div>
                {entries.length === 0 && isActive && (
                  <span className="manifest-message manifest-message-active">Running…</span>
                )}
                {entries.map((entry, i) => (
                  <span className="manifest-message" key={i}>
                    {entry.message}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
