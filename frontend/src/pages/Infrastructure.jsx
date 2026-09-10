import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  CircleAlert,
  MapPin,
  Route,
  Search,
  ShieldAlert,
} from "lucide-react";

import { api } from "../services/api";

const RISK_ORDER = [
  "CRITICAL",
  "EXTREME",
  "VERY HIGH",
  "HIGH",
  "ELEVATED",
  "MODERATE",
  "LOW",
  "NO DATA",
];

const RISK_COLORS = {
  CRITICAL: "#991b1b",
  EXTREME: "#991b1b",
  "VERY HIGH": "#ef4444",
  HIGH: "#f97316",
  ELEVATED: "#f59e0b",
  MODERATE: "#facc15",
  LOW: "#22c55e",
  "NO DATA": "#94a3b8",
};

function normalizeRisk(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "NO DATA";
  }

  const text = String(value)
    .trim()
    .toUpperCase()
    .replace(/-/g, "_")
    .replace(/\s+/g, "_");

  if (
    text === "EXTREME" ||
    text === "CRITICAL"
  ) {
    return "CRITICAL";
  }

  if (text === "VERY_HIGH") {
    return "VERY HIGH";
  }

  if (text === "HIGH") {
    return "HIGH";
  }

  if (text === "ELEVATED") {
    return "ELEVATED";
  }

  if (text === "MODERATE") {
    return "MODERATE";
  }

  if (text === "LOW") {
    return "LOW";
  }

  return "NO DATA";
}

function getRisk(item) {
  const props =
    item?.properties || item || {};

  const direct =
    props.risk_category ??
    props.risk_class ??
    props.risk_level ??
    props.priority ??
    props.risk;

  if (
    direct !== undefined &&
    direct !== null
  ) {
    return normalizeRisk(direct);
  }

  const numeric =
    props.risk_score ??
    props.dynamic_risk ??
    props.risk_value ??
    props.score;

  if (
    numeric !== undefined &&
    numeric !== null
  ) {
    const value = Number(numeric);

    if (!Number.isNaN(value)) {
      if (value >= 0.95) return "CRITICAL";
      if (value >= 0.85) return "VERY HIGH";
      if (value >= 0.70) return "HIGH";
      if (value >= 0.50) return "ELEVATED";
      if (value >= 0.30) return "MODERATE";
      return "LOW";
    }
  }

  return "NO DATA";
}

function getName(item, fallback) {
  const props =
    item?.properties || item || {};

  return (
    props.name ||
    props.NAME ||
    props.Name ||
    props.road_name ||
    props.highway ||
    props.ref ||
    fallback
  );
}

function getCoordinates(item) {
  const geometry =
    item?.geometry;

  if (
    geometry?.type === "Point" &&
    geometry.coordinates?.length >= 2
  ) {
    return {
      lon: geometry.coordinates[0],
      lat: geometry.coordinates[1],
    };
  }

  if (
    item?.lon !== undefined &&
    item?.lat !== undefined
  ) {
    return {
      lon: item.lon,
      lat: item.lat,
    };
  }

  return null;
}

function RiskBadge({ risk }) {
  return (
    <span
      className="infra-risk-badge"
      style={{
        borderColor:
          RISK_COLORS[risk],
        color:
          RISK_COLORS[risk],
      }}
    >
      {risk}
    </span>
  );
}

function KPI({
  icon,
  label,
  value,
  sub,
}) {
  return (
    <div className="infra-kpi">
      <div className="infra-kpi-icon">
        {icon}
      </div>

      <div>
        <div className="infra-kpi-label">
          {label}
        </div>

        <div className="infra-kpi-value">
          {value}
        </div>

        <div className="infra-kpi-sub">
          {sub}
        </div>
      </div>
    </div>
  );
}

export default function Infrastructure() {

  const [roads, setRoads] = useState([]);
  const [settlements, setSettlements] =
    useState([]);

  const [search, setSearch] =
    useState("");

  const [filter, setFilter] =
    useState("ALL");

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState(null);

  useEffect(() => {

    let active = true;

    setLoading(true);
    setError(null);

    Promise.all([
      api.roads(),
      api.settlements(),
    ])
      .then(
        ([
          roadData,
          settlementData,
        ]) => {

          if (!active) return;

          setRoads(
            Array.isArray(roadData)
              ? roadData
              : []
          );

          setSettlements(
            Array.isArray(
              settlementData
            )
              ? settlementData
              : []
          );
        }
      )
      .catch((err) => {

        console.error(
          "Infrastructure error:",
          err
        );

        if (active) {
          setError(
            "Infrastructure data could not be loaded."
          );
        }
      })
      .finally(() => {

        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };

  }, []);

  const roadStats = useMemo(() => {

    const counts = {};

    RISK_ORDER.forEach(
      (risk) => {
        counts[risk] = 0;
      }
    );

    roads.forEach((road) => {
      counts[getRisk(road)]++;
    });

    return counts;

  }, [roads]);

  const settlementStats =
    useMemo(() => {

      const counts = {};

      RISK_ORDER.forEach(
        (risk) => {
          counts[risk] = 0;
        }
      );

      settlements.forEach(
        (settlement) => {
          counts[
            getRisk(settlement)
          ]++;
        }
      );

      return counts;

    }, [settlements]);

  const roadHighPlus =
    roadStats.HIGH +
    roadStats["VERY HIGH"] +
    roadStats.CRITICAL;

  const settlementHighPlus =
    settlementStats.HIGH +
    settlementStats["VERY HIGH"] +
    settlementStats.CRITICAL;

  const criticalTotal =
    roadStats.CRITICAL +
    settlementStats.CRITICAL;

  const filteredRoads =
    useMemo(() => {

      const q =
        search.trim().toLowerCase();

      return roads
        .map((item) => ({
          item,
          risk: getRisk(item),
        }))
        .filter(({ item, risk }) => {

          if (
            filter !== "ALL" &&
            risk !== filter
          ) {
            return false;
          }

          if (!q) return true;

          const props =
            item?.properties || item;

          return JSON.stringify(
            props
          )
            .toLowerCase()
            .includes(q);
        })
        .slice(0, 100);

    }, [roads, search, filter]);

  const filteredSettlements =
    useMemo(() => {

      const q =
        search.trim().toLowerCase();

      return settlements
        .map((item) => ({
          item,
          risk: getRisk(item),
        }))
        .filter(({ item, risk }) => {

          if (
            filter !== "ALL" &&
            risk !== filter
          ) {
            return false;
          }

          if (!q) return true;

          const props =
            item?.properties || item;

          return JSON.stringify(
            props
          )
            .toLowerCase()
            .includes(q);
        })
        .slice(0, 100);

    }, [
      settlements,
      search,
      filter,
    ]);

  if (loading) {
    return (
      <main className="page">
        <div className="infra-loading">
          Loading infrastructure intelligence…
        </div>
      </main>
    );
  }

  return (
    <main className="page">

      {/* HEADER */}

      <div className="infra-header">

        <div>
          <span className="eyebrow">
            EXPOSURE INTELLIGENCE
          </span>

          <h2>
            Infrastructure Risk
          </h2>

          <p>
            Roads and settlements
            potentially exposed to
            dynamic landslide risk.
          </p>
        </div>

        <div className="infra-status">
          <ShieldAlert size={18} />
          Decision-support analysis
        </div>

      </div>

      {error && (
        <div className="banner-error">
          {error}
        </div>
      )}

      {/* KPI ROW */}

      <section className="infra-kpis">

        <KPI
          icon={<Route size={21} />}
          label="ROADS ANALYSED"
          value={roads.length.toLocaleString()}
          sub="Road segments in dataset"
        />

        <KPI
          icon={<Building2 size={21} />}
          label="SETTLEMENTS"
          value={settlements.length.toLocaleString()}
          sub="Mapped settlement points"
        />

        <KPI
          icon={<AlertTriangle size={21} />}
          label="HIGH+ ROADS"
          value={roadHighPlus.toLocaleString()}
          sub="High, very high or critical"
        />

        <KPI
          icon={<CircleAlert size={21} />}
          label="HIGH+ SETTLEMENTS"
          value={settlementHighPlus.toLocaleString()}
          sub="Potentially exposed"
        />

        <KPI
          icon={<ShieldAlert size={21} />}
          label="CRITICAL"
          value={criticalTotal.toLocaleString()}
          sub="Highest-priority assets"
        />

      </section>

      {/* RISK DISTRIBUTION */}

      <section className="infra-grid">

        <div className="infra-card">

          <div className="infra-card-title">
            <div>
              <h3>
                Road Risk Distribution
              </h3>
              <span>
                Classified infrastructure
              </span>
            </div>

            <Route size={20} />
          </div>

          <div className="infra-bars">

            {RISK_ORDER
              .filter(
                (risk) =>
                  roadStats[risk] > 0
              )
              .map((risk) => {

                const value =
                  roadStats[risk];

                const percentage =
                  roads.length
                    ? (
                        value /
                        roads.length
                      ) *
                      100
                    : 0;

                return (
                  <div
                    className="infra-bar-row"
                    key={risk}
                  >

                    <div className="infra-bar-label">
                      <span>
                        <i
                          style={{
                            background:
                              RISK_COLORS[
                                risk
                              ],
                          }}
                        />
                        {risk}
                      </span>

                      <strong>
                        {value.toLocaleString()}
                      </strong>
                    </div>

                    <div className="infra-bar-track">
                      <div
                        className="infra-bar-fill"
                        style={{
                          width:
                            `${Math.max(
                              percentage,
                              value > 0
                                ? 1
                                : 0
                            )}%`,
                          background:
                            RISK_COLORS[
                              risk
                            ],
                        }}
                      />
                    </div>

                    <small>
                      {percentage.toFixed(
                        1
                      )}
                      %
                    </small>

                  </div>
                );
              })}

          </div>

        </div>

        <div className="infra-card">

          <div className="infra-card-title">
            <div>
              <h3>
                Settlement Risk
              </h3>
              <span>
                Potentially exposed locations
              </span>
            </div>

            <MapPin size={20} />
          </div>

          <div className="infra-bars">

            {RISK_ORDER
              .filter(
                (risk) =>
                  settlementStats[
                    risk
                  ] > 0
              )
              .map((risk) => {

                const value =
                  settlementStats[
                    risk
                  ];

                const percentage =
                  settlements.length
                    ? (
                        value /
                        settlements.length
                      ) *
                      100
                    : 0;

                return (
                  <div
                    className="infra-bar-row"
                    key={risk}
                  >

                    <div className="infra-bar-label">
                      <span>
                        <i
                          style={{
                            background:
                              RISK_COLORS[
                                risk
                              ],
                          }}
                        />

                        {risk}
                      </span>

                      <strong>
                        {value.toLocaleString()}
                      </strong>
                    </div>

                    <div className="infra-bar-track">
                      <div
                        className="infra-bar-fill"
                        style={{
                          width:
                            `${Math.max(
                              percentage,
                              value > 0
                                ? 1
                                : 0
                            )}%`,
                          background:
                            RISK_COLORS[
                              risk
                            ],
                        }}
                      />
                    </div>

                    <small>
                      {percentage.toFixed(
                        1
                      )}
                      %
                    </small>

                  </div>
                );
              })}

          </div>

        </div>

      </section>

      {/* TABLE */}

      <section className="infra-card infra-table-card">

        <div className="infra-table-header">

          <div>
            <h3>
              Infrastructure Priority Register
            </h3>

            <span>
              Inspect assets by calculated risk class
            </span>
          </div>

          <div className="infra-controls">

            <div className="infra-search">
              <Search size={16} />

              <input
                value={search}
                onChange={(e) =>
                  setSearch(
                    e.target.value
                  )
                }
                placeholder="Search infrastructure..."
              />
            </div>

            <select
              value={filter}
              onChange={(e) =>
                setFilter(
                  e.target.value
                )
              }
            >
              <option value="ALL">
                All risk levels
              </option>

              {RISK_ORDER
                .filter(
                  (risk) =>
                    risk !== "NO DATA"
                )
                .map((risk) => (
                  <option
                    value={risk}
                    key={risk}
                  >
                    {risk}
                  </option>
                ))}
            </select>

          </div>

        </div>

        <div className="infra-table-wrap">

          <table className="infra-table">

            <thead>
              <tr>
                <th>Infrastructure</th>
                <th>Type</th>
                <th>Risk</th>
                <th>Coordinates</th>
                <th>Status</th>
              </tr>
            </thead>

            <tbody>

              {filteredRoads
                .slice(0, 50)
                .map(
                  ({
                    item,
                    risk,
                  }, index) => {

                    const coordinates =
                      getCoordinates(
                        item
                      );

                    return (
                      <tr
                        key={`road-row-${index}`}
                      >

                        <td>
                          {getName(
                            item,
                            `Road segment ${index + 1}`
                          )}
                        </td>

                        <td>
                          <span className="infra-type">
                            <Route size={14} />
                            Road
                          </span>
                        </td>

                        <td>
                          <RiskBadge
                            risk={risk}
                          />
                        </td>

                        <td>
                          {coordinates
                            ? `${coordinates.lat.toFixed(
                                4
                              )}, ${coordinates.lon.toFixed(
                                4
                              )}`
                            : "—"}
                        </td>

                        <td>
                          {risk ===
                            "CRITICAL" ||
                          risk ===
                            "VERY HIGH" ? (
                            <span className="infra-priority">
                              <AlertTriangle
                                size={14}
                              />
                              Priority
                            </span>
                          ) : (
                            <span className="infra-normal">
                              <CheckCircle2
                                size={14}
                              />
                              Monitor
                            </span>
                          )}
                        </td>

                      </tr>
                    );
                  }
                )}

              {filteredSettlements
                .slice(0, 50)
                .map(
                  ({
                    item,
                    risk,
                  }, index) => {

                    const coordinates =
                      getCoordinates(
                        item
                      );

                    return (
                      <tr
                        key={`settlement-row-${index}`}
                      >

                        <td>
                          {getName(
                            item,
                            `Settlement ${index + 1}`
                          )}
                        </td>

                        <td>
                          <span className="infra-type">
                            <Building2
                              size={14}
                            />
                            Settlement
                          </span>
                        </td>

                        <td>
                          <RiskBadge
                            risk={risk}
                          />
                        </td>

                        <td>
                          {coordinates
                            ? `${coordinates.lat.toFixed(
                                4
                              )}, ${coordinates.lon.toFixed(
                                4
                              )}`
                            : "—"}
                        </td>

                        <td>
                          {risk ===
                            "CRITICAL" ||
                          risk ===
                            "VERY HIGH" ? (
                            <span className="infra-priority">
                              <AlertTriangle
                                size={14}
                              />
                              Priority
                            </span>
                          ) : (
                            <span className="infra-normal">
                              <CheckCircle2
                                size={14}
                              />
                              Monitor
                            </span>
                          )}
                        </td>

                      </tr>
                    );
                  }
                )}

            </tbody>

          </table>

          {!filteredRoads.length &&
            !filteredSettlements.length && (
              <div className="infra-empty">
                No infrastructure matches
                the selected filter.
              </div>
            )}

        </div>

      </section>

      {/* DISCLAIMER */}

      <div className="infra-disclaimer">
        <AlertTriangle size={15} />

        Risk classes represent model-based
        decision-support estimates. They are
        not official disaster warnings or
        guaranteed landslide predictions.
      </div>

    </main>
  );
}