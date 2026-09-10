import React from "react";
import { NavLink } from "react-router-dom";
import { Mountain, CalendarDays, RefreshCw } from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "Overview", end: true },
  { to: "/risk-map", label: "Risk Map" },
  { to: "/infrastructure", label: "Infrastructure" },
  { to: "/model", label: "Model Insights" },
];

export default function TopNav({ date, setDate, onRefresh, loading, apiOnline }) {
  return (
    <header className="topnav">
      <div className="topnav-brand">
        <div className="brand-icon">
          <Mountain size={18} />
        </div>
        <div className="brand-text">
          <b>
            LANDSLIDE<span>AI</span>
          </b>
          <small>GEOSPATIAL RISK INTELLIGENCE</small>
        </div>
      </div>

      <nav className="topnav-links">
        {NAV_ITEMS.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end}>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="topnav-actions">
        <label className="date-control">
          <CalendarDays size={14} />
          <span className="date-label">SCENARIO</span>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </label>

        <button
          type="button"
          className="refresh icon-only"
          onClick={onRefresh}
          title="Refresh current scenario data"
        >
          <RefreshCw size={14} className={loading ? "spin" : ""} />
        </button>

        <div className={`live ${apiOnline === false ? "offline" : ""}`}>
          <span className="live-dot" />
          {apiOnline === false ? "API OFFLINE" : "API ONLINE"}
        </div>
      </div>
    </header>
  );
}
