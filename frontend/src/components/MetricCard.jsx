import React from "react";

export default function MetricCard({ label, value, sub, tone = "neutral", icon: Icon }) {
  return (
    <div className={`metric ${tone}`}>
      {Icon && (
        <div className="metric-icon">
          <Icon size={16} />
        </div>
      )}
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value ?? "-"}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}
