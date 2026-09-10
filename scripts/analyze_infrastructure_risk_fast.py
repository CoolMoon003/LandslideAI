import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.sample import sample_gen

BASE_DIR = r"C:\Users\Naveen\Desktop\YHACK-LANDSLIDE"

ROAD_FILE = os.path.join(
    BASE_DIR, "data", "raw", "osm", "roads.geojson"
)

SETTLEMENT_FILE = os.path.join(
    BASE_DIR, "data", "raw", "osm", "settlements.geojson"
)

RISK_RASTER = os.path.join(
    BASE_DIR,
    "data", "processed", "risk",
    "dynamic_risk_2022-06-21.tif"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR, "data", "processed", "infrastructure"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


def risk_category(v):
    if np.isnan(v):
        return "NO DATA"
    if v < 0.20:
        return "LOW"
    if v < 0.35:
        return "MODERATE"
    if v < 0.50:
        return "ELEVATED"
    if v < 0.65:
        return "HIGH"
    if v < 0.80:
        return "VERY HIGH"
    return "EXTREME"


def priority(v):
    if np.isnan(v):
        return "NO DATA"
    if v >= 0.80:
        return "CRITICAL"
    if v >= 0.65:
        return "VERY HIGH"
    if v >= 0.50:
        return "HIGH"
    if v >= 0.35:
        return "MODERATE"
    return "LOW"


print("=" * 70)
print("YHACK LANDSLIDE AI - FAST INFRASTRUCTURE RISK ANALYSIS")
print("=" * 70)

# ============================================================
# LOAD RASTER
# ============================================================

print("\n[1] Loading risk raster...")

src = rasterio.open(RISK_RASTER)

print(f"Raster: {src.height} x {src.width}")
print(f"CRS: {src.crs}")
print(f"Bounds: {src.bounds}")


# ============================================================
# LOAD ROADS
# ============================================================

print("\n[2] Loading roads...")

roads = gpd.read_file(ROAD_FILE)

if roads.crs != src.crs:
    roads = roads.to_crs(src.crs)

print(f"Roads: {len(roads):,}")


# ============================================================
# FAST ROAD SAMPLING
# ============================================================

print("\n[3] Sampling road risk...")

# Instead of repeatedly reading the whole raster,
# collect all sample points first and perform one
# efficient raster sampling operation.

sample_points = []
road_ids = []

for idx, geom in enumerate(roads.geometry):

    if geom is None or geom.is_empty:
        continue

    # Handle LineString / MultiLineString
    lines = (
        list(geom.geoms)
        if geom.geom_type == "MultiLineString"
        else [geom]
    )

    for line in lines:

        if line.length == 0:
            continue

        # 7 points per line is sufficient for the
        # infrastructure overview.
        for fraction in np.linspace(0, 1, 7):

            point = line.interpolate(
                float(fraction),
                normalized=True
            )

            sample_points.append(
                (point.x, point.y)
            )

            road_ids.append(idx)

    if (idx + 1) % 5000 == 0:
        print(
            f"Prepared {idx + 1:,} / "
            f"{len(roads):,} roads"
        )


print(f"\nTotal sample points: {len(sample_points):,}")

# ============================================================
# ONE BATCH RASTER READ
# ============================================================

print("\n[4] Reading raster values...")

values = []

for value in sample_gen(src, sample_points):

    v = value[0]

    if src.nodata is not None and v == src.nodata:
        values.append(np.nan)
    else:
        values.append(float(v))

values = np.array(values)

print("Raster sampling complete.")


# ============================================================
# AGGREGATE ROAD RESULTS
# ============================================================

print("\n[5] Calculating road statistics...")

sample_df = pd.DataFrame({
    "road_id": road_ids,
    "risk": values
})

sample_df["high_or_worse"] = (
    sample_df["risk"] >= 0.50
)

stats = sample_df.groupby("road_id").agg(
    mean_dynamic_risk=("risk", "mean"),
    max_dynamic_risk=("risk", "max"),
    high_or_worse_fraction=("high_or_worse", "mean")
)

roads["mean_dynamic_risk"] = roads.index.map(
    stats["mean_dynamic_risk"]
)

roads["max_dynamic_risk"] = roads.index.map(
    stats["max_dynamic_risk"]
)

roads["high_or_worse_fraction"] = roads.index.map(
    stats["high_or_worse_fraction"]
)

roads["risk_category"] = roads[
    "max_dynamic_risk"
].apply(risk_category)


# ============================================================
# ROAD PRIORITY
# ============================================================

print("\n[6] Creating road priorities...")

def road_priority(row):

    risk = row["max_dynamic_risk"]

    highway = str(
        row.get("highway", "")
    ).lower()

    major = highway in [
        "motorway",
        "trunk",
        "primary",
        "secondary"
    ]

    if np.isnan(risk):
        return "NO DATA"

    if risk >= 0.80 and major:
        return "CRITICAL"

    if risk >= 0.65 and major:
        return "VERY HIGH"

    if risk >= 0.50:
        return "HIGH"

    if risk >= 0.35:
        return "MODERATE"

    return "LOW"


roads["priority"] = roads.apply(
    road_priority,
    axis=1
)


# ============================================================
# SAVE ROAD RESULTS
# ============================================================

print("\n[7] Saving road results...")

road_csv = os.path.join(
    OUTPUT_DIR,
    "roads_risk_analysis.csv"
)

road_geojson = os.path.join(
    OUTPUT_DIR,
    "roads_risk_analysis.geojson"
)

roads.drop(
    columns="geometry"
).to_csv(
    road_csv,
    index=False
)

roads.to_file(
    road_geojson,
    driver="GeoJSON"
)

print(f"Saved: {road_csv}")
print(f"Saved: {road_geojson}")


# ============================================================
# SETTLEMENTS
# ============================================================

print("\n[8] Loading settlements...")

settlements = gpd.read_file(
    SETTLEMENT_FILE
)

if settlements.crs != src.crs:
    settlements = settlements.to_crs(src.crs)

print(
    f"Settlements: "
    f"{len(settlements):,}"
)


# ============================================================
# FAST SETTLEMENT SAMPLING
# ============================================================

print("\n[9] Sampling settlement risk...")

settlement_points = []

for geom in settlements.geometry:

    if geom is None or geom.is_empty:
        settlement_points.append((np.nan, np.nan))
    else:
        settlement_points.append(
            (geom.x, geom.y)
        )

valid_indices = [
    i for i, p in enumerate(settlement_points)
    if not np.isnan(p[0])
]

valid_points = [
    settlement_points[i]
    for i in valid_indices
]

settlement_values = np.full(
    len(settlements),
    np.nan
)

if valid_points:

    sampled = list(
        sample_gen(
            src,
            valid_points
        )
    )

    for i, value in zip(
        valid_indices,
        sampled
    ):

        v = value[0]

        if src.nodata is None or v != src.nodata:
            settlement_values[i] = float(v)


settlements["dynamic_risk"] = settlement_values

settlements["risk_category"] = (
    settlements["dynamic_risk"]
    .apply(risk_category)
)

settlements["priority"] = (
    settlements["dynamic_risk"]
    .apply(priority)
)


# ============================================================
# SAVE SETTLEMENT RESULTS
# ============================================================

print("\n[10] Saving settlement results...")

settlement_csv = os.path.join(
    OUTPUT_DIR,
    "settlements_risk_analysis.csv"
)

settlement_geojson = os.path.join(
    OUTPUT_DIR,
    "settlements_risk_analysis.geojson"
)

settlements.drop(
    columns="geometry"
).to_csv(
    settlement_csv,
    index=False
)

settlements.to_file(
    settlement_geojson,
    driver="GeoJSON"
)

print(f"Saved: {settlement_csv}")
print(f"Saved: {settlement_geojson}")


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("INFRASTRUCTURE ANALYSIS COMPLETE")
print("=" * 70)

print("\nROAD RISK DISTRIBUTION")
print(
    roads["risk_category"]
    .value_counts()
    .to_string()
)

print("\nROAD PRIORITY DISTRIBUTION")
print(
    roads["priority"]
    .value_counts()
    .to_string()
)

print("\nSETTLEMENT RISK DISTRIBUTION")
print(
    settlements["risk_category"]
    .value_counts()
    .to_string()
)

print("\nSETTLEMENT PRIORITY DISTRIBUTION")
print(
    settlements["priority"]
    .value_counts()
    .to_string()
)

print("\nTOP 15 EXPOSED ROADS")

print(
    roads[
        [
            "name",
            "highway",
            "mean_dynamic_risk",
            "max_dynamic_risk",
            "high_or_worse_fraction",
            "priority"
        ]
    ]
    .sort_values(
        "max_dynamic_risk",
        ascending=False
    )
    .head(15)
    .to_string(index=False)
)

print("\nTOP 15 EXPOSED SETTLEMENTS")

print(
    settlements[
        [
            "name",
            "place",
            "dynamic_risk",
            "risk_category",
            "priority"
        ]
    ]
    .sort_values(
        "dynamic_risk",
        ascending=False
    )
    .head(15)
    .to_string(index=False)
)

src.close()

print("\nDone.")