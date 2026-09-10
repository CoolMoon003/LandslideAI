import React, { useEffect, useState } from "react";
import { AlertCircle, MapPin, Route, Building2 } from "lucide-react";
import { api } from "../services/api";
import RiskBadge from "./RiskBadge";

const SEVERITY_ORDER = {
  EXTREME: 6,
  "VERY HIGH": 5,
  HIGH: 4,
  ELEVATED: 3,
  MODERATE: 2,
  LOW: 1,
  "NO DATA": 0,
};

function normalizeRisk(val) {
  if (val === null || val === undefined || val === "") return "NO DATA";
  const str = String(val).trim().toUpperCase().replace(/[-_]+/g, " ");
  if (str === "CRITICAL" || str === "EXTREME") return "EXTREME";
  if (str === "VERY HIGH") return "VERY HIGH";
  if (str === "HIGH") return "HIGH";
  if (str === "ELEVATED") return "ELEVATED";
  if (str === "MODERATE") return "MODERATE";
  if (str === "LOW") return "LOW";
  return "NO DATA";
}

function getRiskValue(item) {
  const p = item?.properties || item?.props || item || {};
  const raw =
    p.risk_class ??
    p.risk ??
    p.risk_category ??
    p.Risk_Class ??
    p.RISK_CLASS ??
    p.priority ??
    null;

  const normalized = normalizeRisk(raw);
  if (normalized !== "NO DATA") return normalized;

  // Check numeric risk score as fallback if categorical field was missing/NO DATA
  const numeric =
    p.dynamic_risk ??
    p.mean_dynamic_risk ??
    p.max_dynamic_risk ??
    p.risk_score;

  if (numeric != null && !Number.isNaN(Number(numeric))) {
    const v = Number(numeric);
    if (v >= 0.95) return "EXTREME";
    if (v >= 0.85) return "VERY HIGH";
    if (v >= 0.70) return "HIGH";
    if (v >= 0.50) return "ELEVATED";
    if (v >= 0.30) return "MODERATE";
    return "LOW";
  }

  return "NO DATA";
}

function getSeverityRank(risk) {
  return SEVERITY_ORDER[risk] ?? 0;
}

function getRoadName(properties) {
  const p = properties || {};
  const name = p.name || p.NAME || p.Name;
  if (name && String(name).trim()) return String(name).trim();

  const ref = p.ref || p.REF;
  if (ref && String(ref).trim()) return String(ref).trim();

  const highway = p.highway || p.HIGHWAY;
  if (highway && String(highway).trim()) {
    const hwStr = String(highway).trim();
    return `${hwStr.charAt(0).toUpperCase() + hwStr.slice(1)} segment`;
  }

  return "High-risk road segment";
}

function getSettlementName(properties) {
  const p = properties || {};
  const name = p.name || p.NAME || p.Name;
  if (name && String(name).trim()) return String(name).trim();

  const place = p.place || p.PLACE;
  if (place && String(place).trim()) {
    const plStr = String(place).trim();
    return `${plStr.charAt(0).toUpperCase() + plStr.slice(1)} settlement`;
  }

  const type = p.type || p.TYPE;
  if (type && String(type).trim()) {
    return `${String(type).trim()} settlement`;
  }

  return "High-risk settlement";
}

function getRoadCoordinates(geometry) {
  if (!geometry) return null;
  const coords =
    geometry.type === "LineString"
      ? geometry.coordinates
      : geometry.type === "MultiLineString" && geometry.coordinates?.[0]
      ? geometry.coordinates[0]
      : null;
  if (coords && coords.length) {
    return coords[Math.floor(coords.length / 2)];
  }
  return null;
}

function getSettlementCoordinates(geometry) {
  if (!geometry) return null;
  if (geometry.type === "Point" && geometry.coordinates) {
    return geometry.coordinates;
  }
  return null;
}

export default function MonitoringAlerts({ date, refreshKey, onAlertSelect }) {
  const [alerts, setAlerts] = useState([]);
  const [totalCount, setTotalCount] = useState(null);
  const [loading, setLoading] = useState(true);
  const [apiUnavailable, setApiUnavailable] = useState(false);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setApiUnavailable(false);

    async function loadAlerts() {
      try {
        const [roadsRaw, settlementsRaw] = await Promise.all([
          api.roads(),
          api.settlements(),
        ]);

        const qualifyingRoadAlerts = (roadsRaw || [])
          .map((feature) => {
            const props = feature.properties || feature || {};
            const risk = getRiskValue(feature);
            const priority = normalizeRisk(
              props.priority ?? props.priority_level ?? props.risk_priority ?? risk
            );
            return {
              type: "ROAD",
              name: getRoadName(props),
              risk,
              priority,
              rank: getSeverityRank(risk),
              coordinates: getRoadCoordinates(feature.geometry),
              properties: props,
              geometry: feature.geometry,
            };
          })
          .filter((alert) => alert.rank >= 4); // HIGH, VERY HIGH, EXTREME

        const qualifyingSettlementAlerts = (settlementsRaw || [])
          .map((feature) => {
            const props = feature.properties || feature || {};
            const risk = getRiskValue(feature);
            const priority = normalizeRisk(
              props.priority ?? props.priority_level ?? props.risk_priority ?? risk
            );
            return {
              type: "SETTLEMENT",
              name: getSettlementName(props),
              risk,
              priority,
              rank: getSeverityRank(risk),
              coordinates: getSettlementCoordinates(feature.geometry),
              properties: props,
              geometry: feature.geometry,
            };
          })
          .filter((alert) => alert.rank >= 4); // HIGH, VERY HIGH, EXTREME

        const allQualifying = [...qualifyingRoadAlerts, ...qualifyingSettlementAlerts];

        // Sort descending by severity (EXTREME > VERY HIGH > HIGH)
        allQualifying.sort((a, b) => b.rank - a.rank);

        if (mounted) {
          setTotalCount(allQualifying.length);
          setAlerts(allQualifying.slice(0, 5));
          setApiUnavailable(false);
        }
      } catch (error) {
        console.error("Monitoring alerts fetch failed:", error);
        if (mounted) {
          setApiUnavailable(true);
          setTotalCount(null);
          setAlerts([]);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadAlerts();

    return () => {
      mounted = false;
    };
  }, [date, refreshKey]);

  // Badge status representation
  let badgeText = "Checking...";
  let badgeClass = "map-badge";

  if (loading) {
    badgeText = "Updating...";
  } else if (apiUnavailable) {
    badgeText = "Monitoring unavailable";
    badgeClass = "map-badge badge-warning";
  } else if (totalCount === 0) {
    badgeText = "No active high-risk alerts";
  } else {
    badgeText = `${totalCount} ACTIVE`;
    badgeClass = "map-badge badge-active";
  }

  return (
    <div className="alerts-card card">
      <div className="card-head">
        <div>
          <p className="card-kicker">Infrastructure intelligence</p>
          <h3 className="card-title">Monitoring Alerts</h3>
          <p className="card-subtitle">
            Real high-risk infrastructure identified for scenario {date || "2022-06-21"}
          </p>
        </div>

        <div className={badgeClass}>{badgeText}</div>
      </div>

      {loading ? (
        <div className="empty">Loading infrastructure intelligence...</div>
      ) : apiUnavailable ? (
        <div className="empty compact">
          <AlertCircle size={20} />
          <div>Monitoring unavailable: unable to reach infrastructure API.</div>
        </div>
      ) : alerts.length === 0 ? (
        <div className="empty compact">
          <MapPin size={20} />
          <div>No active high-risk alerts detected for this scenario.</div>
        </div>
      ) : (
        <div className="alert-list">
          {alerts.map((alert, index) => {
            const sevClass =
              alert.risk === "EXTREME"
                ? "sev-extreme"
                : alert.risk === "VERY HIGH"
                ? "sev-very-high"
                : "sev-high";
            const actionLabel = alert.risk === "HIGH" ? "Review exposure" : "Prioritize monitoring";
            const actionClass = alert.risk === "HIGH" ? "review" : "urgent";

            return (
              <div
                key={`${alert.type}-${index}`}
                className={`alert-item ${sevClass}`}
                onClick={() => onAlertSelect?.(alert)}
                style={{ cursor: onAlertSelect ? "pointer" : "default" }}
                title={onAlertSelect ? "Click to view location on map" : undefined}
              >
                <div className="alert-icon">
                  {alert.type === "ROAD" ? <Route size={15} /> : <Building2 size={15} />}
                </div>

                <div className="alert-content">
                  <div className="alert-title-row">
                    <RiskBadge value={alert.risk} />
                    <span className="alert-type-tag">{alert.type}</span>
                  </div>
                  <strong>{alert.name}</strong>
                  <span className="alert-meta">
                    Risk: {alert.risk}
                    {alert.priority && alert.priority !== "NO DATA" && alert.priority !== alert.risk
                      ? ` • ${alert.priority} priority`
                      : ""}
                  </span>
                </div>

                <span className={`alert-action-tag ${actionClass}`}>{actionLabel}</span>
              </div>
            );
          })}
        </div>
      )}

      <div className="data-note" style={{ marginTop: 14 }}>
        <Route size={12} style={{ verticalAlign: "middle", marginRight: 5 }} />
        Road and settlement risk records are derived directly from the scenario model output.
      </div>
    </div>
  );
}