from pathlib import Path

import geopandas as gpd
import pandas as pd
import rasterio


ROOT = Path(__file__).resolve().parents[1]

GSI_PATH = (
    ROOT
    / "data"
    / "processed"
    / "meghalaya_landslides.geojson"
)

TERRAIN_DIR = ROOT / "data" / "processed" / "terrain"

WORLDCOVER_PATH = (
    ROOT
    / "data"
    / "raw"
    / "landcover"
    / "meghalaya_worldcover_2021_10m.tif"
)

OUTPUT_PATH = (
    ROOT
    / "data"
    / "processed"
    / "meghalaya_static_features.csv"
)


print("=" * 70)
print("YHACK LANDSLIDE AI - STATIC FEATURE EXTRACTION")
print("=" * 70)


# ---------------------------------------------------------
# LOAD GSI
# ---------------------------------------------------------

print("\n[1] Loading Meghalaya landslides...")

gsi = gpd.read_file(GSI_PATH)

print("Total Meghalaya records:", len(gsi))


# ---------------------------------------------------------
# OPEN RASTERS
# ---------------------------------------------------------

print("\n[2] Opening raster datasets...")

raster_paths = {
    "elevation": TERRAIN_DIR / "elevation.tif",
    "slope": TERRAIN_DIR / "slope.tif",
    "aspect": TERRAIN_DIR / "aspect.tif",
    "curvature": TERRAIN_DIR / "curvature.tif",
}

rasters = {}

for name, path in raster_paths.items():

    src = rasterio.open(path)
    rasters[name] = src

    print(
        f"{name:12s} | "
        f"CRS={src.crs} | "
        f"resolution={src.res}"
    )


worldcover = rasterio.open(WORLDCOVER_PATH)

print(
    "worldcover   | "
    f"CRS={worldcover.crs} | "
    f"resolution={worldcover.res}"
)


# ---------------------------------------------------------
# REPROJECT POINTS
# ---------------------------------------------------------

target_crs = rasters["elevation"].crs

gsi = gsi.to_crs(target_crs)


# ---------------------------------------------------------
# EXTRACT FEATURES
# ---------------------------------------------------------

print("\n[3] Extracting raster values...")

coordinates = [
    (point.x, point.y)
    for point in gsi.geometry
]

feature_data = {}

for name, src in rasters.items():

    values = []

    for value in src.sample(coordinates):

        values.append(float(value[0]))

    feature_data[name] = values

    print(f"Extracted {name}")


# WorldCover

worldcover_values = []

for value in worldcover.sample(coordinates):

    worldcover_values.append(int(value[0]))

feature_data["landcover_class"] = worldcover_values

print("Extracted landcover_class")


# ---------------------------------------------------------
# BUILD DATAFRAME
# ---------------------------------------------------------

print("\n[4] Building feature table...")

df = pd.DataFrame(feature_data)

# Original attributes we want to preserve

df["latitude"] = gsi["LATITUDE"].values
df["longitude"] = gsi["LONGITUDE"].values
df["district"] = gsi["DISTRICT"].values
df["initiation_year"] = pd.to_numeric(
    gsi["INITIATION"],
    errors="coerce"
)

df["triggering"] = (
    gsi["TRIGGERING"]
    .fillna("")
    .astype(str)
    .str.strip()
)

# Every GSI point is a positive landslide example

df["label"] = 1


# ---------------------------------------------------------
# REMOVE INVALID FEATURES
# ---------------------------------------------------------

print("\n[5] Checking extracted values...")

print("\nMissing values:")

print(df.isna().sum())

# Remove rows with invalid terrain values

required_features = [
    "elevation",
    "slope",
    "aspect",
    "curvature",
    "landcover_class",
]

before = len(df)

df = df.dropna(subset=required_features)

after = len(df)

print(
    f"\nRemoved {before - after} records "
    f"with missing feature values."
)


# ---------------------------------------------------------
# STATISTICS
# ---------------------------------------------------------

print("\n[6] Feature statistics")

print(
    df[
        [
            "elevation",
            "slope",
            "aspect",
            "curvature",
            "landcover_class",
        ]
    ].describe()
)


# ---------------------------------------------------------
# LANDCOVER DISTRIBUTION
# ---------------------------------------------------------

print("\n[7] WorldCover classes at landslide locations")

print(
    df["landcover_class"]
    .value_counts()
    .sort_index()
)


# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

df.to_csv(
    OUTPUT_PATH,
    index=False
)

print("\nSaved:")
print(OUTPUT_PATH)


# ---------------------------------------------------------
# CLOSE RASTERS
# ---------------------------------------------------------

for src in rasters.values():
    src.close()

worldcover.close()


print("\n" + "=" * 70)
print("STATIC FEATURE EXTRACTION COMPLETE")
print("=" * 70)