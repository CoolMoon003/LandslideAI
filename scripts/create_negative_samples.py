"""
YHACK LANDSLIDE AI
Create negative/background samples for static susceptibility modeling.

Positive samples:
    Known GSI landslide locations

Negative samples:
    Random locations across the Meghalaya study area,
    filtered so they are sufficiently far from known landslides.

Output:
    data/processed/meghalaya_training_static.csv
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from shapely.geometry import Point
from shapely.ops import unary_union


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

LANDSLIDE_FILE = (
    BASE_DIR / "data" / "processed" / "meghalaya_landslides.geojson"
)

STATIC_FILE = (
    BASE_DIR / "data" / "processed" / "meghalaya_static_features.csv"
)

DEM_FILE = (
    BASE_DIR / "data" / "processed" / "terrain" / "elevation.tif"
)

SLOPE_FILE = (
    BASE_DIR / "data" / "processed" / "terrain" / "slope.tif"
)

ASPECT_FILE = (
    BASE_DIR / "data" / "processed" / "terrain" / "aspect.tif"
)

CURVATURE_FILE = (
    BASE_DIR / "data" / "processed" / "terrain" / "curvature.tif"
)

WORLDCOVER_FILE = (
    BASE_DIR / "data" / "raw" / "landcover" / "meghalaya_worldcover_2021_10m.tif"
)

OUTPUT_FILE = (
    BASE_DIR / "data" / "processed" / "meghalaya_training_static.csv"
)


# Number of negative samples we want
RANDOM_SEED = 42

# Keep negative points at least this far from known landslides.
# This is intentionally conservative for a hackathon baseline.
MIN_DISTANCE_METERS = 1000

# Generate more candidates than needed because many will be rejected.
CANDIDATE_MULTIPLIER = 8


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def sample_raster(raster_path, points):
    """
    Sample raster values at point coordinates.

    Returns:
        numpy array of sampled values.
    """

    with rasterio.open(raster_path) as src:

        # Reproject points if necessary
        coords = [(point.x, point.y) for point in points]

        values = []

        for value in src.sample(coords):

            if len(value) > 0:
                values.append(value[0])
            else:
                values.append(np.nan)

        return np.array(values)


def get_valid_raster_mask(dem_path):
    """
    Create a polygon representing the valid DEM coverage.
    """

    with rasterio.open(dem_path) as src:

        # Raster bounds
        left = src.bounds.left
        bottom = src.bounds.bottom
        right = src.bounds.right
        top = src.bounds.top

        from shapely.geometry import box

        return box(left, bottom, right, top), src.crs


def generate_random_points(bounds, count, rng):
    """
    Generate random points inside bounding box.
    """

    minx, miny, maxx, maxy = bounds

    xs = rng.uniform(minx, maxx, count)
    ys = rng.uniform(miny, maxy, count)

    return [
        Point(x, y)
        for x, y in zip(xs, ys)
    ]


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("YHACK LANDSLIDE AI - NEGATIVE SAMPLE GENERATION")
    print("=" * 70)

    rng = np.random.default_rng(RANDOM_SEED)

    # --------------------------------------------------------
    # 1. Load positive landslide samples
    # --------------------------------------------------------

    print("\n[1] Loading positive landslide samples...")

    positive_df = pd.read_csv(STATIC_FILE)

    print(f"Positive samples available: {len(positive_df)}")

    if "label" in positive_df.columns:
        positive_df["label"] = 1

    # --------------------------------------------------------
    # 2. Load GSI points
    # --------------------------------------------------------

    print("\n[2] Loading GSI landslide geometry...")

    landslides = gpd.read_file(LANDSLIDE_FILE)

    # Meghalaya already filtered in previous step,
    # but filter again for safety.
    if "STATE" in landslides.columns:

        landslides["STATE_CLEAN"] = (
            landslides["STATE"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        landslides = landslides[
            landslides["STATE_CLEAN"] == "meghalaya"
        ].copy()

    print(f"GSI Meghalaya records: {len(landslides)}")

    # Remove invalid geometries
    landslides = landslides[
        landslides.geometry.notnull()
    ].copy()

    # --------------------------------------------------------
    # 3. Open DEM
    # --------------------------------------------------------

    print("\n[3] Opening DEM...")

    with rasterio.open(DEM_FILE) as dem:

        dem_crs = dem.crs
        dem_bounds = dem.bounds

        print(f"DEM CRS: {dem_crs}")
        print(f"DEM bounds: {dem_bounds}")

    # --------------------------------------------------------
    # 4. Convert landslides to metric CRS
    # --------------------------------------------------------

    print("\n[4] Preparing distance calculation...")

    # Meghalaya is mostly covered by UTM Zone 46N.
    # EPSG:32646 gives distances in meters.
    METRIC_CRS = "EPSG:32646"

    landslides_metric = landslides.to_crs(METRIC_CRS)

    positive_geometries = list(
        landslides_metric.geometry
    )

    # Spatial index for faster distance filtering
    landslide_union = unary_union(
        positive_geometries
    )

    print(
        f"Minimum negative-to-landslide distance: "
        f"{MIN_DISTANCE_METERS} meters"
    )

    # --------------------------------------------------------
    # 5. Generate random candidates
    # --------------------------------------------------------

    print("\n[5] Generating random candidate points...")

    # Convert DEM boundary to metric CRS
    dem_boundary = gpd.GeoSeries(
        [get_valid_raster_mask(DEM_FILE)[0]],
        crs=dem_crs
    ).to_crs(METRIC_CRS).iloc[0]

    target_negative_count = len(positive_df)

    candidate_count = (
        target_negative_count * CANDIDATE_MULTIPLIER
    )

    print(f"Target negatives: {target_negative_count}")
    print(f"Candidate points: {candidate_count}")

    candidate_points = generate_random_points(
        dem_boundary.bounds,
        candidate_count,
        rng
    )

    # --------------------------------------------------------
    # 6. Keep points inside DEM boundary
    # --------------------------------------------------------

    print("\n[6] Filtering candidates by DEM coverage...")

    inside_points = []

    for point in candidate_points:

        if dem_boundary.contains(point):

            inside_points.append(point)

    print(
        f"Candidates inside DEM coverage: "
        f"{len(inside_points)}"
    )

    # --------------------------------------------------------
    # 7. Remove points too close to landslides
    # --------------------------------------------------------

    print("\n[7] Removing points near known landslides...")

    negative_points_metric = []

    for point in inside_points:

        distance = point.distance(landslide_union)

        if distance >= MIN_DISTANCE_METERS:

            negative_points_metric.append(point)

        if len(negative_points_metric) >= target_negative_count:
            break

    print(
        f"Valid negative samples: "
        f"{len(negative_points_metric)}"
    )

    # --------------------------------------------------------
    # 8. Safety check
    # --------------------------------------------------------

    if len(negative_points_metric) < target_negative_count:

        print("\nWARNING:")
        print(
            "Not enough valid negative samples were generated."
        )
        print(
            f"Required: {target_negative_count}"
        )
        print(
            f"Generated: {len(negative_points_metric)}"
        )

        raise RuntimeError(
            "Could not generate enough negative samples. "
            "Try reducing MIN_DISTANCE_METERS."
        )

    # Keep exact target count
    negative_points_metric = negative_points_metric[
        :target_negative_count
    ]

    # --------------------------------------------------------
    # 9. Convert negative points back to raster CRS
    # --------------------------------------------------------

    print("\n[8] Converting negative points to raster CRS...")

    negative_gdf = gpd.GeoDataFrame(
        {
            "geometry": negative_points_metric
        },
        crs=METRIC_CRS
    )

    negative_gdf = negative_gdf.to_crs(dem_crs)

    negative_points = list(
        negative_gdf.geometry
    )

    # --------------------------------------------------------
    # 10. Extract terrain features
    # --------------------------------------------------------

    print("\n[9] Extracting terrain features...")

    elevation = sample_raster(
        DEM_FILE,
        negative_points
    )

    slope = sample_raster(
        SLOPE_FILE,
        negative_points
    )

    aspect = sample_raster(
        ASPECT_FILE,
        negative_points
    )

    curvature = sample_raster(
        CURVATURE_FILE,
        negative_points
    )

    landcover = sample_raster(
        WORLDCOVER_FILE,
        negative_points
    )

    print("Extracted elevation")
    print("Extracted slope")
    print("Extracted aspect")
    print("Extracted curvature")
    print("Extracted landcover")

    # --------------------------------------------------------
    # 11. Build negative dataframe
    # --------------------------------------------------------

    print("\n[10] Building negative feature table...")

    negative_df = pd.DataFrame(
        {
            "elevation": elevation,
            "slope": slope,
            "aspect": aspect,
            "curvature": curvature,
            "landcover_class": landcover,
            "latitude": [
                point.y for point in negative_points
            ],
            "longitude": [
                point.x for point in negative_points
            ],
            "district": "background",
            "initiation_year": np.nan,
            "triggering": "background",
            "label": 0,
        }
    )

    # --------------------------------------------------------
    # 12. Remove invalid raster values
    # --------------------------------------------------------

    print("\n[11] Checking negative sample values...")

    required_features = [
        "elevation",
        "slope",
        "aspect",
        "curvature",
        "landcover_class",
    ]

    missing_before = negative_df[
        required_features
    ].isna().sum()

    print("\nMissing values:")
    print(missing_before)

    negative_df = negative_df.dropna(
        subset=required_features
    ).reset_index(drop=True)

    print(
        f"\nValid negatives after cleaning: "
        f"{len(negative_df)}"
    )

    # --------------------------------------------------------
    # 13. Make positive + negative dataset
    # --------------------------------------------------------

    print("\n[12] Combining positive and negative samples...")

    # Make sure positive data has exactly the same core columns
    feature_columns = [
        "elevation",
        "slope",
        "aspect",
        "curvature",
        "landcover_class",
        "latitude",
        "longitude",
        "district",
        "initiation_year",
        "triggering",
        "label",
    ]

    positive_df = positive_df[
        feature_columns
    ].copy()

    negative_df = negative_df[
        feature_columns
    ].copy()

    # If some negatives were lost because of NaN values,
    # randomly reduce positives to maintain balance.
    if len(negative_df) < len(positive_df):

        print(
            "\nNegative samples were reduced after cleaning."
        )

        print(
            f"Positive samples: {len(positive_df)}"
        )

        print(
            f"Negative samples: {len(negative_df)}"
        )

        positive_df = positive_df.sample(
            n=len(negative_df),
            random_state=RANDOM_SEED
        ).reset_index(drop=True)

    else:

        negative_df = negative_df.sample(
            n=len(positive_df),
            random_state=RANDOM_SEED
        ).reset_index(drop=True)

    combined_df = pd.concat(
        [
            positive_df,
            negative_df
        ],
        ignore_index=True
    )

    # --------------------------------------------------------
    # 14. Shuffle dataset
    # --------------------------------------------------------

    combined_df = combined_df.sample(
        frac=1,
        random_state=RANDOM_SEED
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # 15. Final statistics
    # --------------------------------------------------------

    print("\n[13] Final dataset statistics")

    print("-" * 70)

    print(
        f"Total samples: {len(combined_df)}"
    )

    print(
        f"Positive samples: "
        f"{(combined_df['label'] == 1).sum()}"
    )

    print(
        f"Negative samples: "
        f"{(combined_df['label'] == 0).sum()}"
    )

    print("\nFeature statistics:")

    print(
        combined_df[
            required_features
        ].describe()
    )

    print("\nClass distribution:")

    print(
        combined_df["label"].value_counts()
    )

    # --------------------------------------------------------
    # 16. Save
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    combined_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\nSaved:")
    print(OUTPUT_FILE)

    print("\n" + "=" * 70)
    print("NEGATIVE SAMPLE GENERATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()