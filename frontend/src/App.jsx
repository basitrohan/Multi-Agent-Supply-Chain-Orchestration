import { useEffect, useState } from "react";
import StressTestForm from "./components/StressTestForm";
import DataPanel from "./components/DataPanel";
import AgentManifest from "./components/AgentManifest";
import ResultsPanel from "./components/ResultsPanel";
import { api, ApiError } from "./lib/api";

export default function App() {
  const [health, setHealth] = useState(null);
  const [summary, setSummary] = useState(null);
  const [pipeline, setPipeline] = useState({ status: "idle", auditLog: [] });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    refreshSummary();
    api
      .health()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  function refreshSummary() {
    api
      .dataSummary()
      .then(setSummary)
      .catch(() => setSummary(null));
  }

  async function handleRunStressTest(formValues) {
    setError(null);
    setResult(null);
    setPipeline({ status: "running", auditLog: [] });

    try {
      const response = await api.runStressTest(formValues);
      setPipeline({ status: "done", auditLog: response.audit_log || [] });
      setResult(response);
    } catch (err) {
      setPipeline({ status: "idle", auditLog: [] });
      if (err instanceof ApiError) {
        setError(err.detail?.errors ? err.detail.errors.join(" ") : err.message);
      } else {
        setError("Something went wrong running the stress test.");
      }
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-brand">
          <span className="brand-mark">SC</span>
          <div className="brand-text">
            <span className="brand-name">SupplyChain Sentinel</span>
            <span className="brand-tagline">Multi-agent stress-test console</span>
          </div>
        </div>
        <div className="topbar-status">
          <span className={`status-dot ${health ? "status-dot-ok" : "status-dot-off"}`} />
          <span className="status-text">
            {health
              ? `Connected · ${health.bedrock_mode === "live" ? "AWS Bedrock" : "Offline report engine"}`
              : "Backend not reachable"}
          </span>
        </div>
      </header>

      {error && (
        <div className="error-banner">
          <strong>Run failed.</strong> {error}
        </div>
      )}

      <main className="layout">
        <div className="layout-col layout-col-left">
          <StressTestForm onSubmit={handleRunStressTest} isRunning={pipeline.status === "running"} />
          <DataPanel summary={summary} onDataChanged={refreshSummary} />
        </div>

        <div className="layout-col layout-col-mid">
          <AgentManifest auditLog={pipeline.auditLog} status={pipeline.status} />
        </div>

        <div className="layout-col layout-col-right">
          <ResultsPanel result={result} />
        </div>
      </main>
    </div>
  );
}
