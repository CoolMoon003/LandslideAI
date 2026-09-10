import React from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

const RISK_COLORS = {
  LOW: "#22a06b",
  MODERATE: "#e3b93a",
  ELEVATED: "#f0973f",
  HIGH: "#ef7a53",
  "VERY HIGH": "#e0453f",
  EXTREME: "#8f1f26",
};

function toArray(data) {
  if (Array.isArray(data)) return data;

  if (!data || typeof data !== "object") return [];

  // Common API wrappers
  if (Array.isArray(data.features)) return data.features;
  if (Array.isArray(data.data)) return data.data;
  if (Array.isArray(data.items)) return data.items;
  if (Array.isArray(data.results)) return data.results;

  // Feature importance may be returned as:
  // { slope: 0.46, elevation: 0.25, ... }
  return Object.entries(data)
    .filter(([, value]) => typeof value === "number")
    .map(([key, value]) => ({
      feature: key,
      importance: value,
    }));
}

export function FeatureChart({ data }) {
  const raw = toArray(data);

  const chartData = raw
    .map((item) => {
      if (!item || typeof item !== "object") return null;

      const name =
        item.feature ??
        item.name ??
        item.feature_name ??
        item.label ??
        Object.keys(item)[0];

      const value =
        item.importance ??
        item.value ??
        item.score ??
        item.weight ??
        0;

      return {
        name: String(name).replaceAll("_", " "),
        value: Number(value) || 0,
      };
    })
    .filter(Boolean)
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);

  if (!chartData.length) {
    return (
      <div className="empty-chart">
        No feature-importance data available.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 10, right: 25, left: 20, bottom: 10 }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          type="number"
          domain={[0, "auto"]}
          tickFormatter={(value) =>
            `${(Number(value) * 100).toFixed(0)}%`
          }
        />
        <YAxis
          type="category"
          dataKey="name"
          width={100}
        />
        <Tooltip
          formatter={(value) =>
            `${(Number(value) * 100).toFixed(2)}%`
          }
        />
        <Bar
          dataKey="value"
          name="Importance"
          radius={[0, 4, 4, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function DistributionChart({ data }) {
  const classes = Array.isArray(data?.classes) ? data.classes : [];

  if (!classes.length) {
    return (
      <div className="empty-chart">
        No dynamic risk distribution available for this scenario.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={classes}
          dataKey="pct"
          nameKey="class"
          innerRadius={55}
          outerRadius={90}
          paddingAngle={2}
        >
          {classes.map((c) => (
            <Cell key={c.class} fill={RISK_COLORS[c.class] || "#8996a2"} />
          ))}
        </Pie>
        <Tooltip formatter={(value, name) => [`${Number(value).toFixed(1)}%`, name]} />
        <Legend
          layout="vertical"
          align="right"
          verticalAlign="middle"
          formatter={(value) => <span className="legend-text">{value}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function RainChart({ data }) {
  const chartData = toArray(data);

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" hide />
        <YAxis />
        <Tooltip />
        <Line
          type="monotone"
          dataKey="rainfall"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
