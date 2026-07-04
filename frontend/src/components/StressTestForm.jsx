import { useState } from "react";
import Card from "./Card";

const DISRUPTION_TYPES = [
  { value: "port_closure", label: "Port closure" },
  { value: "supplier_delay", label: "Supplier delay" },
  { value: "demand_spike", label: "Demand spike" },
  { value: "raw_material_shortage", label: "Raw material shortage" },
  { value: "logistics_disruption", label: "Logistics disruption" },
];

const REGIONS = ["APAC", "North America", "EU", "global"];

export default function StressTestForm({ onSubmit, isRunning }) {
  const [form, setForm] = useState({
    scenario_name: "West Coast Port Closure",
    disruption_type: "port_closure",
    affected_region: "APAC",
    severity: 0.7,
    duration_days: 21,
  });

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    onSubmit(form);
  }

  return (
    <Card className="form-card">
      <h2 className="card-heading">Run a stress test</h2>
      <p className="card-subhead">
        Describe a disruption scenario. The agent pipeline will assess risk, simulate
        the impact, and forecast the result.
      </p>

      <form onSubmit={handleSubmit} className="stress-form">
        <label className="field">
          <span className="field-label">Scenario name</span>
          <input
            type="text"
            value={form.scenario_name}
            onChange={(e) => update("scenario_name", e.target.value)}
            required
          />
        </label>

        <div className="field-row">
          <label className="field">
            <span className="field-label">Disruption type</span>
            <select
              value={form.disruption_type}
              onChange={(e) => update("disruption_type", e.target.value)}
            >
              {DISRUPTION_TYPES.map((d) => (
                <option key={d.value} value={d.value}>
                  {d.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span className="field-label">Affected region</span>
            <select
              value={form.affected_region}
              onChange={(e) => update("affected_region", e.target.value)}
            >
              {REGIONS.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="field">
          <span className="field-label">
            Severity <span className="mono field-value">{Math.round(form.severity * 100)}%</span>
          </span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={form.severity}
            onChange={(e) => update("severity", parseFloat(e.target.value))}
          />
        </label>

        <label className="field">
          <span className="field-label">Duration (days)</span>
          <input
            type="number"
            min="1"
            max="365"
            value={form.duration_days}
            onChange={(e) => update("duration_days", parseInt(e.target.value, 10) || 1)}
          />
        </label>

        <button type="submit" className="btn-primary" disabled={isRunning}>
          {isRunning ? "Running pipeline…" : "Run stress test"}
        </button>
      </form>
    </Card>
  );
}
