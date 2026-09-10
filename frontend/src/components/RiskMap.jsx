import React, { useEffect, useMemo, useState } from "react";

import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Polyline,
  Popup,
  ImageOverlay,
  useMap,
  useMapEvents,
} from "react-leaflet";

import RiskLegend from "./RiskLegend";
import { api } from "../services/api";

const center = [25.55, 91.35];

const MAX_ROADS_ON_MAP = 6000;
const MAX_LANDSLIDES_ON_MAP = 1200;
const MAX_SETTLEMENTS_ON_MAP = 1200;

const RISK = {
  LOW: {
    color: "#22c55e",
    label: "LOW",
  },
  MODERATE: {
    color: "#facc15",
    label: "MODERATE",
  },
  ELEVATED: {
    color: "#f59e0b",
    label: "ELEVATED",
  },
  HIGH: {
    color: "#f97316",
    label: "HIGH",
  },
  VERY_HIGH: {
    color: "#ef4444",
    label: "VERY HIGH",
  },
  EXTREME: {
    color: "#991b1b",
    label: "CRITICAL",
  },
  CRITICAL: {
    color: "#991b1b",
    label: "CRITICAL",
  },
};

function normalizeRisk(value) {
  if (value === null || value === undefined || value === "") {
    return "NO DATA";
  }

  const text = String(value)
    .trim()
    .toUpperCase()
    .replace(/-/g, "_")
    .replace(/\s+/g, "_");

  if (text === "EXTREME") return "EXTREME";
  if (text === "CRITICAL") return "CRITICAL";
  if (text === "VERY_HIGH") return "VERY_HIGH";
  if (text === "HIGH") return "HIGH";
  if (text === "ELEVATED") return "ELEVATED";
  if (text === "MODERATE") return "MODERATE";
  if (text === "LOW") return "LOW";

  return "NO DATA";
}

function getRiskFromProperties(properties = {}) {
  const direct =
    properties.risk_category ??
    properties.risk_class ??
    properties.risk_level ??
    properties.priority ??
    properties.risk;

  if (direct !== undefined && direct !== null) {
    return normalizeRisk(direct);
  }

  const numeric =
    properties.risk_score ??
    properties.dynamic_risk ??
    properties.risk_value ??
    properties.score;

  if (numeric !== undefined && numeric !== null) {
    const value = Number(numeric);

    if (!Number.isNaN(value)) {
      if (value >= 0.95) return "EXTREME";
      if (value >= 0.85) return "VERY_HIGH";
      if (value >= 0.70) return "HIGH";
      if (value >= 0.50) return "ELEVATED";
      if (value >= 0.30) return "MODERATE";
      return "LOW";
    }
  }

  return "NO DATA";
}

function riskColor(risk) {
  return RISK[risk]?.color || "#94a3b8";
}

function riskLabel(risk) {
  return RISK[risk]?.label || risk.replaceAll("_", " ");
}

function FitMap({ bounds }) {
  const map = useMap();

  useEffect(() => {
    if (!bounds) return;

    map.fitBounds(bounds, {
      padding: [30, 30],
    });
  }, [map, bounds]);

  return null;
}

// Generic map-click -> server-side raster sample, per the risk/point
// endpoint. This is what actually lets someone click empty terrain (not
// just an existing road/settlement/landslide marker) and see a real risk
// score + category for that spot.
function PointInspector({ date, onPick, disabled }) {
  useMapEvents({
    click(e) {
      if (disabled) return;

      const { lat, lng: lon } = e.latlng;

      // Show a loading state immediately, then replace it once the API
      // responds — never fabricate a value while waiting.
      onPick({
        kind: "Location",
        lat,
        lon,
        date,
        loading: true,
      });

      api
        .point(lat, lon, date)
        .then((result) => {
          onPick({
            kind: "Location",
            lat,
            lon,
            date,
            loading: false,
            riskScore: result?.risk ?? null,
            riskCategory: result?.category || "NO DATA",
          });
        })
        .catch((err) => {
          console.error("risk/point lookup failed:", err);
          onPick({
            kind: "Location",
            lat,
            lon,
            date,
            loading: false,
            riskScore: null,
            riskCategory: "NO DATA",
            error: "Could not reach the risk API for this point.",
          });
        });
    },
  });

  return null;
}

export default function RiskMap({
  date,
  landslides = [],
  settlements = [],
  roads = [],
  selected,
  setSelected,
  scenario,
  compact = false,
}) {
  const points = Array.isArray(landslides)
    ? landslides
    : landslides?.features || [];

  const places = Array.isArray(settlements)
    ? settlements
    : settlements?.features || [];

  const roadLines = Array.isArray(roads)
    ? roads
    : roads?.features || [];

  const overlayBounds = useMemo(() => {
    if (!scenario?.bounds || scenario.bounds.length !== 4) {
      return null;
    }

    const [left, bottom, right, top] = scenario.bounds;

    return [
      [bottom, left],
      [top, right],
    ];
  }, [scenario]);

  const overlayUrl = api.overlayUrl(date);

  const select = (payload) => {
    if (setSelected) {
      setSelected(payload);
    }
  };

  return (
    <div className={`map-wrap ${compact ? "compact" : ""}`}>

      <MapContainer
        center={center}
        zoom={compact ? 7 : 8}
        scrollWheelZoom={!compact}
        dragging={!compact}
        zoomControl={!compact}
        doubleClickZoom={!compact}
        className="risk-map"
      >

        {/* BASE MAP */}

        <TileLayer
          attribution="© OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* DYNAMIC RISK RASTER
            Keep this BELOW markers/roads using zIndex */}
        {overlayBounds && (
          <ImageOverlay
            key={`${date}-${overlayUrl}`}
            url={overlayUrl}
            bounds={overlayBounds}
            opacity={0.48}
            zIndex={1}
          />
        )}

        {overlayBounds && (
          <FitMap bounds={overlayBounds} />
        )}

        <PointInspector date={date} onPick={select} disabled={compact} />

        {/* =====================================================
            ROADS
            ===================================================== */}

        {!compact &&
          roadLines
            .slice(0, MAX_ROADS_ON_MAP)
            .map((feature, index) => {

              const geometry = feature.geometry;

              if (!geometry) return null;

              const lines =
                geometry.type === "LineString"
                  ? [geometry.coordinates]
                  : geometry.type === "MultiLineString"
                  ? geometry.coordinates
                  : [];

              const properties =
                feature.properties || {};

              const risk =
                getRiskFromProperties(properties);

              const color =
                riskColor(risk);

              return lines.map(
                (coords, lineIndex) => {

                  if (!coords?.length) {
                    return null;
                  }

                  const middle =
                    coords[
                      Math.floor(
                        coords.length / 2
                      )
                    ];

                  return (
                    <Polyline
                      key={`road-${index}-${lineIndex}`}
                      positions={coords.map(
                        ([lon, lat]) => [
                          lat,
                          lon,
                        ]
                      )}
                      pane="markerPane"
                      pathOptions={{
                        color,
                        weight:
                          risk === "EXTREME" ||
                          risk === "CRITICAL"
                            ? 4
                            : risk === "VERY_HIGH"
                            ? 3
                            : risk === "HIGH"
                            ? 2.5
                            : 1.8,
                        opacity:
                          risk === "NO DATA"
                            ? 0.25
                            : 0.9,
                      }}
                      eventHandlers={{
                        click: () => {

                          if (!middle) return;

                          const [
                            lon,
                            lat,
                          ] = middle;

                          select({
                            kind: "Road",
                            lat,
                            lon,
                            props: {
                              ...properties,
                              risk_category:
                                riskLabel(risk),
                            },
                          });
                        },
                      }}
                    />
                  );
                }
              );
            })}

        {/* =====================================================
            HISTORICAL GSI LANDSLIDES
            BLACK OUTLINE + RED FILL
            ===================================================== */}

        {points
          .slice(0, MAX_LANDSLIDES_ON_MAP)
          .map((feature, index) => {

            const coordinates =
              feature.geometry?.coordinates ||
              [feature.lon, feature.lat];

            if (
              !coordinates ||
              coordinates.length < 2
            ) {
              return null;
            }

            const [lon, lat] = coordinates;

            const properties =
              feature.properties || {};

            return (
              <CircleMarker
                key={`landslide-${index}`}
                center={[lat, lon]}
                pane="markerPane"
                radius={compact ? 3.5 : 6}
                pathOptions={{
                  color: "#000000",
                  fillColor: "#ff0000",
                  fillOpacity: 1,
                  weight: 2,
                }}
                eventHandlers={{
                  click: () =>
                    select({
                      kind:
                        "Historical GSI Landslide",
                      lat,
                      lon,
                      props: properties,
                    }),
                }}
              >
                {!compact && (
                  <Popup>
                    <b>
                      Historical GSI Landslide
                    </b>

                    <br />

                    District:{" "}
                    {properties.district ||
                      "Meghalaya"}
                  </Popup>
                )}
              </CircleMarker>
            );
          })}

        {/* =====================================================
            SETTLEMENTS
            RISK-COLORED DOTS
            ===================================================== */}

        {places
          .slice(0, MAX_SETTLEMENTS_ON_MAP)
          .map((feature, index) => {

            const coordinates =
              feature.geometry?.coordinates ||
              [feature.lon, feature.lat];

            if (
              !coordinates ||
              coordinates.length < 2
            ) {
              return null;
            }

            const [lon, lat] =
              coordinates;

            const properties =
              feature.properties || feature;

            const risk =
              getRiskFromProperties(
                properties
              );

            const color =
              riskColor(risk);

            return (
              <CircleMarker
                key={`settlement-${index}`}
                center={[lat, lon]}
                pane="markerPane"
                radius={
                  risk === "EXTREME" ||
                  risk === "CRITICAL"
                    ? 9
                    : risk === "VERY_HIGH"
                    ? 8
                    : risk === "HIGH"
                    ? 7
                    : 5
                }
                pathOptions={{
                  color: "#ffffff",
                  fillColor: color,
                  fillOpacity: 1,
                  weight: 2,
                }}
                eventHandlers={{
                  click: () =>
                    select({
                      kind:
                        properties.name ||
                        "Settlement",
                      lat,
                      lon,
                      props: {
                        ...properties,
                        risk_category:
                          riskLabel(risk),
                      },
                    }),
                }}
              >
                {!compact && (
                  <Popup>
                    <b>
                      {properties.name ||
                        "Settlement"}
                    </b>

                    <br />

                    Risk:{" "}
                    <strong>
                      {riskLabel(risk)}
                    </strong>
                  </Popup>
                )}
              </CircleMarker>
            );
          })}

      </MapContainer>

      {/* LEGEND */}

      {!compact && <RiskLegend />}

      {/* SCENARIO LABEL */}

      {!compact && (
        <div className="map-badge">
          DYNAMIC RISK | {date}
        </div>
      )}

    </div>
  );
}