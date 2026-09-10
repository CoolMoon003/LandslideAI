import React, { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";

import TopNav from "./components/TopNav";

import Overview from "./pages/Overview";
import RiskMapPage from "./pages/RiskMapPage";
import Infrastructure from "./pages/Infrastructure";
import ModelInsights from "./pages/ModelInsights";

import { api } from "./services/api";

export default function App() {
  const [date, setDate] = useState("2022-06-21");
  const [loading, setLoading] = useState(false);
  const [apiOnline, setApiOnline] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const checkHealth = async () => {
    try {
      await api.health();
      setApiOnline(true);
    } catch (error) {
      console.warn("Backend is not available yet:", error);
      setApiOnline(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 20000);
    return () => clearInterval(interval);
  }, []);

  const refresh = async () => {
    setLoading(true);
    await checkHealth();
    setRefreshKey((prev) => prev + 1);
    setTimeout(() => setLoading(false), 500);
  };

  return (
    <div className="app">
      <TopNav
        date={date}
        setDate={setDate}
        onRefresh={refresh}
        loading={loading}
        apiOnline={apiOnline}
      />

      <div className="content">
        {apiOnline === false && (
          <div className="banner-error top">
            Can't reach the FastAPI backend at http://127.0.0.1:8000. Start it with{" "}
            <code>uvicorn app.main:app --reload --port 8000</code>.
          </div>
        )}

        <Routes>
          <Route path="/" element={<Overview date={date} refreshKey={refreshKey} />} />
          <Route path="/risk-map" element={<RiskMapPage date={date} refreshKey={refreshKey} />} />
          <Route path="/infrastructure" element={<Infrastructure />} />
          <Route path="/model" element={<ModelInsights />} />
        </Routes>
      </div>
    </div>
  );
}
