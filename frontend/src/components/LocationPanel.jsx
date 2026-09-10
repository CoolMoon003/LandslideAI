import React from "react";
import { X, MapPin, AlertTriangle } from "lucide-react";
import RiskBadge from "./RiskBadge";

function fmtCoord(v) {
  return Number.isFinite(Number(v)) ? Number(v).toFixed(5) : "—";
}

function fmtScore(v) {
  return v === null || v === undefined ? "N/A" : Number(v).toFixed(3);
}

export default function LocationPanel({ item, onClose }) {
  if (!item) return null;

  // Two payload shapes land here:
  //  - a raw map click sampled via GET /api/risk/point -> { riskScore, riskCategory, date, loading }
  //  - a road/settlement/landslide feature click -> { props: {...geojson properties} }
  const isPointSample = item.riskCategory !== undefined || item.loading;

  return (
    <aside className="location-panel">
      <button className="icon-btn close" onClick={onClose} aria-label="Close">
        <X />
      </button>

      <div className="panel-kicker">
        <MapPin size={15} /> SELECTED LOCATION
      </div>

      <h2>{item.kind || "Location"}</h2>

      <div className="coords">
        {fmtCoord(item.lat)}&deg; N&nbsp;&nbsp; {fmtCoord(item.lon)}&deg; E
      </div>

      {item.date && (
        <div className="coords" style={{ marginTop: 2 }}>
          Scenario {item.date}
        </div>
      )}

      {isPointSample ? (
        item.loading ? (
          <div className="detail-risk">
            <AlertTriangle size={17} />
            <span>Sampling raster…</span>
          </div>
        ) : (
          <>
            <div className="detail-risk">
              <AlertTriangle size={17} />
              <span>Risk score</span>
              <b>{fmtScore(item.riskScore)}</b>
            </div>
            <div className="details">
              <div>
                <span>risk category</span>
                <RiskBadge value={item.riskCategory} />
              </div>
            </div>
            {item.error && (
              <div className="details">
                <div>
                  <span>note</span>
                  <b>{item.error}</b>
                </div>
              </div>
            )}
          </>
        )
      ) : (
        <>
          <div className="detail-risk">
            <AlertTriangle size={17} />
            <span>Risk assessment</span>
            <b>{item.props?.priority || item.props?.risk_class || "Available via API"}</b>
          </div>
          <div className="details">
            {Object.entries(item.props || {})
              .slice(0, 8)
              .map(([k, v]) => (
                <div key={k}>
                  <span>{k.replaceAll("_", " ")}</span>
                  <b>{String(v)}</b>
                </div>
              ))}
          </div>
        </>
      )}
    </aside>
  );
}
