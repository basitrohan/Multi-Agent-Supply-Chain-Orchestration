import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import Card from "./Card";
import RiskBadge from "./RiskBadge";

function formatUsd(value) {
  if (value == null) return "—";
  return `$${Math.round(value).toLocaleString()}`;
}

function StatTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-month">Month {label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="chart-tooltip-row">
          <span style={{ color: p.color }}>{p.name}</span>
          <span className="mono">{formatUsd(p.value)}</span>
        </div>
      ))}
    </div>
  );
}

export default function ResultsPanel({ result }) {
  if (!result) {
    return (
      <Card className="results-card results-empty">
        <h2 className="card-heading">Results</h2>
        <p className="empty-state">
          Run a stress test to see the risk assessment, simulation outcome, and
          year-over-year forecast here.
        </p>
      </Card>
    );
  }

  const { risk_assessment: risk, simulation_summary: sim, forecast } = result;
  const chartData = forecast?.monthly_projection?.map((m) => ({
    month: m.month,
    Baseline: m.baseline_revenue_usd,
    Stressed: m.stressed_revenue_usd,
  }));

  // The gap between baseline and stressed revenue is often small relative to
  // total monthly revenue (e.g. a $25k dip on a $4.5M month). Starting the
  // Y-axis at zero would flatten that gap into an invisible line. Instead we
  // zoom the axis to a tight band just below the lowest value in the data,
  // so the actual disruption impact is visually legible.
  let yDomain = ["auto", "auto"];
  if (chartData?.length > 0) {
    const allValues = chartData.flatMap((d) => [d.Baseline, d.Stressed]);
    const min = Math.min(...allValues);
    const max = Math.max(...allValues);
    const pad = Math.max((max - min) * 0.4, max * 0.02);
    yDomain = [Math.max(0, min - pad), max + pad * 0.3];
  }

  return (
    <Card className="results-card">
      <h2 className="card-heading">Results</h2>

      <div className="results-grid">
        <div className="stat-block">
          <span className="stat-label">Risk level</span>
          <RiskBadge level={risk?.risk_level} />
          <span className="stat-sub mono">score {risk?.risk_score?.toFixed(2)}</span>
        </div>

        <div className="stat-block">
          <span className="stat-label">Stockout probability</span>
          <span className="stat-number mono">
            {((sim?.stockout_probability ?? 0) * 100).toFixed(0)}%
          </span>
        </div>

        <div className="stat-block">
          <span className="stat-label">Expected revenue impact</span>
          <span className="stat-number mono">{formatUsd(sim?.expected_revenue_impact_usd)}</span>
        </div>

        <div className="stat-block">
          <span className="stat-label">YoY growth impact</span>
          <span
            className="stat-number mono"
            style={{
              color: (forecast?.growth_delta_pct ?? 0) < 0 ? "var(--signal-rust)" : "var(--signal-teal)",
            }}
          >
            {forecast?.growth_delta_pct > 0 ? "+" : ""}
            {forecast?.growth_delta_pct?.toFixed(1)} pts
          </span>
        </div>
      </div>

      {risk?.key_vulnerabilities?.length > 0 && (
        <div className="vuln-list">
          <span className="field-label">Flagged vulnerabilities</span>
          <ul>
            {risk.key_vulnerabilities.slice(0, 4).map((v, i) => (
              <li key={i}>{v}</li>
            ))}
          </ul>
        </div>
      )}

      {chartData?.length > 0 && (
        <div className="chart-wrap">
          <span className="field-label">12-month revenue forecast</span>
          <span className="chart-caption">Y-axis zoomed to show the gap clearly</span>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="baselineFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--signal-teal)" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="var(--signal-teal)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="stressedFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--signal-amber)" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="var(--signal-amber)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--line)" vertical={false} />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 11, fill: "var(--slate)" }}
                axisLine={{ stroke: "var(--line)" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "var(--slate)" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `$${Math.round(v / 1000)}k`}
                width={48}
                domain={yDomain}
              />
              <Tooltip content={<StatTooltip />} />
              <Area
                type="monotone"
                dataKey="Baseline"
                stroke="var(--signal-teal)"
                fill="url(#baselineFill)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="Stressed"
                stroke="var(--signal-amber)"
                fill="url(#stressedFill)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
          <div className="chart-legend">
            <span className="legend-item">
              <span className="legend-dot" style={{ background: "var(--signal-teal)" }} />
              Baseline
            </span>
            <span className="legend-item">
              <span className="legend-dot" style={{ background: "var(--signal-amber)" }} />
              Stressed
            </span>
          </div>
        </div>
      )}

      {result.report_markdown && (
        <details className="report-details">
          <summary>View full report</summary>
          <pre className="report-text">{result.report_markdown}</pre>
        </details>
      )}
    </Card>
  );
}
