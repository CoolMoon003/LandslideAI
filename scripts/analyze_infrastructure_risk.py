import os
import warnings

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import rowcol
from shapely.geometry import Point

warnings.filterwarnings("ignore")

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = r"C:\Users\Naveen\Desktop\YHACK-LANDSLIDE"

ROAD_FILE = os.path.join(
    BASE_DIR, "data", "raw", "osm", "roads.geojson"
)

SETTLEMENT_FILE = os.path.join(
    BASE_DIR, "data", "raw", "osm", "settlements.geojson"
)

RISK_RASTER = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "risk",
    "dynamic_risk_2022-06-21.tif"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "infrastructure"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# RISK CLASSIFICATION
# ============================================================

def risk_category(value):

    if np.isnan(value):
        return "NO DATA"

    if value < 0.20:
        return "LOW"

    elif value < 0.35:
        return "MODERATE"

    elif value < 0.50:
        return "ELEVATED"

    elif value < 0.65:
        return "HIGH"

    elif value < 0.80:
        return "VERY HIGH"

    else:
        return "EXTREME"


# ============================================================
# SAMPLE RASTER AT POINT
# ============================================================

def sample_raster(src, x, y):

    try:
        row, col = rowcol(src.transform, x, y)

        if (
            row < 0
            or row >= src.height
            or col < 0
            or col >= src.width
        ):
            return np.nan

        value = src.read(1)[row, col]

        if src.nodata is not None and value == src.nodata:
            return np.nan

        return float(value)

    except Exception:
        return np.nan


# ============================================================
# SAMPLE RISK ALONG ROAD
# ============================================================

def sample_road_risk(src, geometry, samples=25):

    if geometry is None or geometry.is_empty:
        return []

    values = []

    # Handle MultiLineString
    if geometry.geom_type == "MultiLineString":
        lines = list(geometry.geoms)
    else:
        lines = [geometry]

    for line in lines:

        if line.length == 0:
            continue

        for i in range(samples):

            fraction = i / max(samples - 1, 1)

            point = line.interpolate(fraction, normalized=True)

            value = sample_raster(
                src,
                point.x,
                point.y
            )

            if not np.isnan(value):
                values.append(value)

    return values


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 75)
    print("YHACK LANDSLIDE AI - INFRASTRUCTURE RISK ANALYSIS")
    print("=" * 75)

    # --------------------------------------------------------
    # 1. CHECK FILES
    # --------------------------------------------------------

    print("\n[1] Checking input files...")

    for file in [
        ROAD_FILE,
        SETTLEMENT_FILE,
        RISK_RASTER
    ]:

        if not os.path.exists(file):
            raise FileNotFoundError(
                f"Missing file:\n{file}"
            )

        print(f"Found: {file}")

    # --------------------------------------------------------
    # 2. LOAD RISK RASTER
    # --------------------------------------------------------

    print("\n[2] Loading dynamic risk raster...")

    src = rasterio.open(RISK_RASTER)

    print(f"Raster dimensions: {src.height} x {src.width}")
    print(f"Raster CRS: {src.crs}")
    print(f"Raster bounds: {src.bounds}")

    # --------------------------------------------------------
    # 3. LOAD ROADS
    # --------------------------------------------------------

    print("\n[3] Loading roads...")

    roads = gpd.read_file(ROAD_FILE)

    print(f"Total roads: {len(roads):,}")
    print(f"Road CRS: {roads.crs}")

    # Make sure CRS matches raster
    if roads.crs != src.crs:
        roads = roads.to_crs(src.crs)

    # --------------------------------------------------------
    # 4. ANALYZE ROADS
    # --------------------------------------------------------

    print("\n[4] Calculating road exposure...")

    road_results = []

    total_roads = len(roads)

    for idx, road in roads.iterrows():

        geometry = road.geometry

        values = sample_road_risk(
            src,
            geometry,
            samples=25
        )

        if len(values) == 0:

            max_risk = np.nan
            mean_risk = np.nan
            high_fraction = 0.0

        else:

            values = np.array(values)

            max_risk = np.max(values)
            mean_risk = np.mean(values)

            # Fraction of sampled road points
            # that are HIGH or worse
            high_fraction = np.mean(values >= 0.50)

        road_results.append({

            "osm_id": road.get("osm_id"),
            "name": road.get("name"),
            "highway": road.get("highway"),

            "mean_dynamic_risk": mean_risk,
            "max_dynamic_risk": max_risk,

            "high_or_worse_fraction": high_fraction,

            "risk_category": risk_category(max_risk),

            "geometry": geometry
        })

        if (idx + 1) % 1000 == 0:

            print(
                f"  Processed {idx + 1:,} / "
                f"{total_roads:,} roads"
            )

    roads_result = gpd.GeoDataFrame(
        road_results,
        geometry="geometry",
        crs=src.crs
    )

    # --------------------------------------------------------
    # 5. ROAD PRIORITY
    # --------------------------------------------------------

    print("\n[5] Creating road priority ranking...")

    def road_priority(row):

        risk = row["max_dynamic_risk"]
        fraction = row["high_or_worse_fraction"]

        highway = str(row["highway"]).lower()

        if np.isnan(risk):
            return "NO DATA"

        # Major roads get higher priority
        major_road = highway in [
            "motorway",
            "trunk",
            "primary",
            "secondary"
        ]

        if risk >= 0.80 and major_road:
            return "CRITICAL"

        if risk >= 0.65 and major_road:
            return "VERY HIGH"

        if risk >= 0.50:
            return "HIGH"

        if risk >= 0.35:
            return "MODERATE"

        return "LOW"

    roads_result["priority"] = roads_result.apply(
        road_priority,
        axis=1
    )

    # --------------------------------------------------------
    # 6. SAVE ROADS
    # --------------------------------------------------------

    road_csv = os.path.join(
        OUTPUT_DIR,
        "roads_risk_analysis.csv"
    )

    road_geojson = os.path.join(
        OUTPUT_DIR,
        "roads_risk_analysis.geojson"
    )

    roads_result.drop(
        columns="geometry"
    ).to_csv(
        road_csv,
        index=False
    )

    roads_result.to_file(
        road_geojson,
        driver="GeoJSON"
    )

    print("\nRoad analysis saved:")
    print(road_csv)
    print(road_geojson)

    # --------------------------------------------------------
    # 7. LOAD SETTLEMENTS
    # --------------------------------------------------------

    print("\n[6] Loading settlements...")

    settlements = gpd.read_file(SETTLEMENT_FILE)

    print(
        f"Total settlements: "
        f"{len(settlements):,}"
    )

    print(
        f"Settlement CRS: "
        f"{settlements.crs}"
    )

    if settlements.crs != src.crs:
        settlements = settlements.to_crs(src.crs)

    # --------------------------------------------------------
    # 8. ANALYZE SETTLEMENTS
    # --------------------------------------------------------

    print("\n[7] Calculating settlement exposure...")

    settlement_results = []

    for idx, settlement in settlements.iterrows():

        geometry = settlement.geometry

        if geometry is None or geometry.is_empty:
            risk = np.nan

        else:
            risk = sample_raster(
                src,
                geometry.x,
                geometry.y
            )

        settlement_results.append({

            "osm_id": settlement.get("osm_id"),
            "name": settlement.get("name"),
            "place": settlement.get("place"),

            "dynamic_risk": risk,

            "risk_category": risk_category(risk),

            "geometry": geometry
        })

    settlements_result = gpd.GeoDataFrame(
        settlement_results,
        geometry="geometry",
        crs=src.crs
    )

    # --------------------------------------------------------
    # 9. SETTLEMENT PRIORITY
    # --------------------------------------------------------

    print("\n[8] Creating settlement priority ranking...")

    def settlement_priority(value):

        if np.isnan(value):
            return "NO DATA"

        if value >= 0.80:
            return "CRITICAL"

        elif value >= 0.65:
            return "VERY HIGH"

        elif value >= 0.50:
            return "HIGH"

        elif value >= 0.35:
            return "MODERATE"

        else:
            return "LOW"

    settlements_result["priority"] = (
        settlements_result["dynamic_risk"]
        .apply(settlement_priority)
    )

    # --------------------------------------------------------
    # 10. SAVE SETTLEMENTS
    # --------------------------------------------------------

    settlement_csv = os.path.join(
        OUTPUT_DIR,
        "settlements_risk_analysis.csv"
    )

    settlement_geojson = os.path.join(
        OUTPUT_DIR,
        "settlements_risk_analysis.geojson"
    )

    settlements_result.drop(
        columns="geometry"
    ).to_csv(
        settlement_csv,
        index=False
    )

    settlements_result.to_file(
        settlement_geojson,
        driver="GeoJSON"
    )

    print("\nSettlement analysis saved:")
    print(settlement_csv)
    print(settlement_geojson)

    # --------------------------------------------------------
    # 11. SUMMARY
    # --------------------------------------------------------

    print("\n" + "=" * 75)
    print("INFRASTRUCTURE RISK ANALYSIS COMPLETE")
    print("=" * 75)

    print("\nROAD RISK DISTRIBUTION")
    print(
        roads_result["risk_category"]
        .value_counts()
        .to_string()
    )

    print("\nROAD PRIORITY DISTRIBUTION")
    print(
        roads_result["priority"]
        .value_counts()
        .to_string()
    )

    print("\nSETTLEMENT RISK DISTRIBUTION")
    print(
        settlements_result["risk_category"]
        .value_counts()
        .to_string()
    )

    print("\nSETTLEMENT PRIORITY DISTRIBUTION")
    print(
        settlements_result["priority"]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # 12. TOP EXPOSED ROADS
    # --------------------------------------------------------

    print("\nTOP 15 EXPOSED ROADS")

    top_roads = roads_result[
        [
            "name",
            "highway",
            "mean_dynamic_risk",
            "max_dynamic_risk",
            "high_or_worse_fraction",
            "priority"
        ]
    ].sort_values(
        "max_dynamic_risk",
        ascending=False
    ).head(15)

    print(
        top_roads.to_string(index=False)
    )

    # --------------------------------------------------------
    # 13. TOP EXPOSED SETTLEMENTS
    # --------------------------------------------------------

    print("\nTOP 15 EXPOSED SETTLEMENTS")

    top_settlements = settlements_result[
        [
            "name",
            "place",
            "dynamic_risk",
            "risk_category",
            "priority"
        ]
    ].sort_values(
        "dynamic_risk",
        ascending=False
    ).head(15)

    print(
        top_settlements.to_string(index=False)
    )

    src.close()

    print("\nDone.")


if __name__ == "__main__":
    main()