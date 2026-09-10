import React from "react";
import { NavLink } from "react-router-dom";
import { LayoutDashboard, Map, Route, BrainCircuit, Activity, Mountain } from "lucide-react";

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon">
          <Mountain size={18} />
        </div>
        <div>
          <b>LANDSLIDE<span>AI</span></b>
          <small>GEOSPATIAL RISK INTELLIGENCE</small>
        </div>
      </div>

      <div className="nav-label">MONITOR</div>
      <nav className="nav">
        <NavLink to="/" end>
          <LayoutDashboard size={18} /> <span>Overview</span>
        </NavLink>
        <NavLink to="/risk-map">
          <Map size={18} /> <span>Risk Map</span>
        </NavLink>
        <NavLink to="/infrastructure">
          <Route size={18} /> <span>Infrastructure</span>
        </NavLink>
      </nav>

      <div className="nav-label">ANALYSIS</div>
      <nav className="nav">
        <NavLink to="/model">
          <BrainCircuit size={18} /> <span>Model Insights</span>
        </NavLink>
      </nav>

      <div className="sidebar-bottom">
        <div className="status">
          <Activity size={15} />
          <div>
            <small>SYSTEM STATUS</small>
            <b><i /> Risk Engine Online</b>
          </div>
        </div>
        <div className="data-note">
          <small>DATA SOURCES</small>
          <span>GSI · DEM · ESA WorldCover</span>
          <span>IMD Rainfall · OpenStreetMap</span>
        </div>
      </div>
    </aside>
  );
}
