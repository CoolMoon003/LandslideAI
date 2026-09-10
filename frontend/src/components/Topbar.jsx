import React from "react";
import { CalendarDays, RefreshCw, Wifi, WifiOff } from "lucide-react";

export default function Topbar({ date, setDate, onRefresh, loading, apiOnline }) {
  return (
    <header className="topbar">
      <div>
        <div className="eyebrow">MEGHALAYA · INDIA</div>
        <h1>Operational Risk Overview</h1>
      </div>

      <div className="top-actions">
        <label className="date-control">
          <CalendarDays size={16} />
          <span className="date-label">SCENARIO</span>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>

        <button
          type="button"
          className="refresh"
          onClick={onRefresh}
          title="Refresh current scenario data"
        >
          <RefreshCw size={15} className={loading ? "spin" : ""} />
          <span>Refresh</span>
        </button>

        <div className={`live ${apiOnline === false ? "offline" : ""}`}>
          <span className="live-dot" />
          {apiOnline === false ? "API OFFLINE" : "API ONLINE"}
        </div>
      </div>
    </header>
  );
}
