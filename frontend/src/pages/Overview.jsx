import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Mountain, Route, Home, AlertTriangle, Building2 } from "lucide-react";
import { api } from "../services/api";
import MetricCard from "../components/MetricCard";
import RiskMap from "../components/RiskMap";
import MonitoringAlerts from "../components/MonitoringAlerts";
import RiskEngine from "../components/RiskEngine";
import RiskDistributionBars from "../components/RiskDistributionBars";

const RAIN_WINDOWS = [
  { key: "rainfall_1d", label: "1 day" },
  { key: "rainfall_3d", label: "3 day" },
  { key: "rainfall_7d", label: "7 day" },
  { key: "rainfall_15d", label: "15 day" },
  { key: "rainfall_30d", label: "30 day" },
];

export default function Overview({ date, refreshKey }) {
  const [summary, setSummary] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [distribution, setDistribution] = useState(null);
  const [landslides, setLandslides] = useState([]);
  const [settlements, setSettlements] = useState([]);
  const [scenario, setScenario] = useState(null);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    Promise.all([
      api.summary(date),
      api.statistics(date).catch(() => null),
      api.distribution(date).catch(() => null),
      api.landslides().catch(() => []),
      api.settlements().catch(() => []),
      api.scenario(date).catch(() => null),
    ])
      .then(([s, stats, dist, ls, st, sc]) => {
        if (!active) return;
        setSummary(s);
        setStatistics(stats);
        setDistribution(dist);
        setLandslides(ls || []);
        setSettlements(st || []);
        setScenario(sc);
      })
      .catch((err) => {
        console.error("Overview loading failed:", err);
        if (active) setError("Some sections could not reach the API. Is the FastAPI backend running on port 8000?");
      })
      .finally(() => active && setLoading(false));

    return () => {
      active = false;
    };
  }, [date, refreshKey]);

  const historical = summary?.historical_landslides ?? 0;
  const roads = summary?.roads ?? 0;
  const settlementsCount = summary?.settlements ?? 0;

  const highRisk =
    summary?.high_plus_risk_fraction != null
      ? `${(Number(summary.high_plus_risk_fraction) * 100).toFixed(1)}%`
      : "N/A";

  const rainRow = summary?.rainfall || {};
  const availableWindows = RAIN_WINDOWS.filter((w) => rainRow[w.key] != null);

  const dynamicRiskMean =
    statistics?.mean != null
      ? Number(statistics.mean).toFixed(3)
      : (summary?.high_plus_risk_fraction != null ? "N/A" : (loading ? "..." : "N/A"));

  return (
    <main className="page">

      <section className="hero">
        <div>
          <span className="pill">MEGHALAYA PILOT · SCENARIO {date}</span>
          <h2>
            Dynamic landslide <em>risk intelligence.</em>
          </h2>
          <p>
            Combine terrain susceptibility, rainfall triggers and infrastructure exposure
            to identify areas that may deserve monitoring and priority.
          </p>
          <Link to="/risk-map" className="primary">
            <Mountain size={14} /> Open dynamic risk map
          </Link>
          <Link to="/infrastructure" className="secondary">
            <Building2 size={14} /> View infrastructure
          </Link>
        </div>

        <div className="hero-stats">
          <div className="hero-stat">
            <small>MEAN DYNAMIC RISK</small>
            <b>{dynamicRiskMean}</b>
          </div>
          <div className="hero-stat">
            <small>SCENARIO DATE</small>
            <b>{date}</b>
          </div>
        </div>
      </section>

      {error && <div className="banner-error">{error}</div>}

      <div className="metrics">
        <MetricCard
          icon={Mountain}
          label="HISTORICAL LANDSLIDES"
          value={historical.toLocaleString()}
          sub="GSI records in Meghalaya"
        />
        <MetricCard
          icon={Route}
          label="ROAD FEATURES"
          value={roads.toLocaleString()}
          sub="OSM infrastructure features"
        />
        <MetricCard
          icon={Home}
          label="SETTLEMENTS"
          value={settlementsCount.toLocaleString()}
          sub="OSM settlement features"
        />
        <MetricCard
          icon={AlertTriangle}
          label="HIGH+ RISK AREA"
          value={highRisk}
          sub={`Selected rainfall scenario`}
          tone="danger"
        />
      </div>

      <div className="two-col">
        <section className="card map-preview-card">
          <div className="card-head">
            <div>
              <span className="card-kicker">RISK MAP</span>
              <h3>Meghalaya dynamic risk landscape</h3>
              <p className="card-subtitle">Terrain + rainfall + exposure</p>
            </div>
            <Link to="/risk-map" className="text-link">Open full map →</Link>
          </div>
          <div className="mini-map-frame">
            <RiskMap
              date={date}
              landslides={landslides}
              settlements={settlements}
              scenario={scenario}
              selected={selectedLocation}
              setSelected={setSelectedLocation}
              compact
            />
          </div>
        </section>

        <MonitoringAlerts
          date={date}
          refreshKey={refreshKey}
          onAlertSelect={(alert) => {
            if (alert?.coordinates) {
              setSelectedLocation({
                kind: alert.type === "ROAD" ? "Road" : "Settlement",
                lat: alert.coordinates[1],
                lon: alert.coordinates[0],
                props: alert.properties || {},
              });
            }
          }}
        />
      </div>

      <div className="two-col">
        <RiskEngine />

        <section className="card">
          <div className="card-head">
            <div>
              <span className="card-kicker">RAINFALL TRIGGER</span>
              <h3>Accumulation windows</h3>
            </div>
          </div>

          {availableWindows.length > 0 ? (
            <div className="rain-grid">
              {availableWindows.map((w) => (
                <div key={w.key} className="rain-cell">
                  <small>{w.label}</small>
                  <b>{Number(rainRow[w.key]).toFixed(1)} mm</b>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty small">
              Multi-day rainfall breakdown not available for this scenario date.
            </div>
          )}

          <div className="stat-grid" style={{ marginTop: 16 }}>
            <div>
              <small>Trigger score</small>
              <strong>{rainRow.trigger_score != null ? Number(rainRow.trigger_score).toFixed(3) : "N/A"}</strong>
            </div>
            <div>
              <small>Risk raster</small>
              <strong>{summary?.risk_raster_available ? "Available" : "Unavailable"}</strong>
            </div>
          </div>
        </section>
      </div>

      <section className="card" style={{ marginTop: 0 }}>
        <div className="card-head">
          <div>
            <span className="card-kicker">DYNAMIC RISK</span>
            <h3>Dynamic risk classes</h3>
          </div>
        </div>
        <RiskDistributionBars data={distribution} />
        <div className="note" style={{ marginTop: 16 }}>
          Computed directly from the dynamic risk raster for scenario {date}. Decision-support
          system — not an official warning.
        </div>
      </section>

    </main>
  );
}
