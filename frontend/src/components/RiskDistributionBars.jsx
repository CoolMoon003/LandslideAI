import React from "react";

const RISK_COLORS = {
  LOW: "#22a06b",
  MODERATE: "#e3b93a",
  ELEVATED: "#f0973f",
  HIGH: "#ef7a53",
  "VERY HIGH": "#e0453f",
  EXTREME: "#8f1f26",
};

export default function RiskDistributionBars({ data }) {
  const classes = Array.isArray(data?.classes) ? data.classes : [];

  if (!classes.length) {
    return <div className="empty-chart">No dynamic risk distribution available for this scenario.</div>;
  }

  const max = Math.max(...classes.map((c) => Number(c.pct) || 0), 1);

  return (
    <div className="risk-dist-grid">
      {classes.map((c) => {
        const pct = Number(c.pct) || 0;
        const color = RISK_COLORS[c.class] || "#8996a2";
        return (
          <div key={c.class} className="risk-dist-item">
            <span className="risk-dist-label">{c.class}</span>
            <span className="risk-dist-value">{pct.toFixed(1)}%</span>
            <div className="risk-dist-track">
              <div
                className="risk-dist-fill"
                style={{ width: `${Math.max((pct / max) * 100, 3)}%`, background: color }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
