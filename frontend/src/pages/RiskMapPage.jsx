import React, { useEffect, useState } from "react";
import { api } from "../services/api";
import RiskMap from "../components/RiskMap";
import LocationPanel from "../components/LocationPanel";

export default function RiskMapPage({ date }) {
  const [ls, setLs] = useState([]);
  const [st, setSt] = useState([]);
  const [rd, setRd] = useState([]);
  const [selected, setSelected] = useState(null);
  const [stats, setStats] = useState({});
  const [scenario, setScenario] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    Promise.all([
      api.landslides(),
      api.settlements(),
      api.roads(),
      api.statistics(date),
      api.scenario(date)
    ])
      .then(([landslides, settlements, roads, statistics, scenarioData]) => {
        if (!active) return;
        setLs(landslides || []);
        setSt(settlements || []);
        setRd(roads || []);
        setStats(statistics || {});
        setScenario(scenarioData || null);
      })
      .catch((err) => {
        console.error("Risk map error:", err);
        if (active) setError("Some map data could not be loaded. Showing what's available.");
      })
      .finally(() => active && setLoading(false));

    return () => {
      active = false;
    };
  }, [date]);

  return (
    <main className="page full">

      <div className="map-header">
        <div>
          <span className="eyebrow">
            SCENARIO | {date}
          </span>

          <h2>Dynamic Landslide Risk Map</h2>

          <p>
            Terrain susceptibility + rainfall trigger |
            30m output grid | rainfall source ~0.25 degree
          </p>
        </div>

        <div className="map-stat">
          <small>MEAN DYNAMIC RISK</small>
          <b>
            {stats.mean != null
              ? Number(stats.mean).toFixed(3)
              : "N/A"}
          </b>
        </div>
      </div>

      {error && <div className="banner-error">{error}</div>}

      <div className="map-card">

        <RiskMap
          date={date}
          landslides={ls}
          settlements={st}
          roads={rd}
          scenario={scenario}
          selected={selected}
          setSelected={setSelected}
        />

        <LocationPanel
          item={selected}
          onClose={() => setSelected(null)}
        />

        {loading && <div className="map-loading">Loading map data…</div>}

      </div>

    </main>
  );
}
