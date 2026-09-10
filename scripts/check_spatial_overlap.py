from pathlib import Path
import geopandas as gpd
import rasterio

ROOT = Path(__file__).resolve().parents[1]

gsi_path = ROOT / "data" / "processed" / "meghalaya_landslides.geojson"
dem_path = ROOT / "data" / "raw" / "dem" / "meghalaya_dem_30m.tif"
wc_path = ROOT / "data" / "raw" / "landcover" / "meghalaya_worldcover_2021_10m.tif"

gsi = gpd.read_file(gsi_path)

print("=" * 70)
print("SPATIAL OVERLAP CHECK")
print("=" * 70)

# ---------------------------------------------------------
# DEM
# ---------------------------------------------------------

with rasterio.open(dem_path) as src:
    dem_bounds = src.bounds
    dem_crs = src.crs

print("\nDEM bounds:")
print(dem_bounds)

# ---------------------------------------------------------
# WORLDCOVER
# ---------------------------------------------------------

with rasterio.open(wc_path) as src:
    wc_bounds = src.bounds
    wc_crs = src.crs

print("\nWorldCover bounds:")
print(wc_bounds)

# ---------------------------------------------------------
# GSI POINTS
# ---------------------------------------------------------

print("\nGSI total:", len(gsi))

# Make sure same CRS
gsi_dem = gsi.to_crs(dem_crs)

# Create bounding-box mask
inside_dem = (
    (gsi_dem.geometry.x >= dem_bounds.left)
    & (gsi_dem.geometry.x <= dem_bounds.right)
    & (gsi_dem.geometry.y >= dem_bounds.bottom)
    & (gsi_dem.geometry.y <= dem_bounds.top)
)

inside_wc = (
    (gsi_dem.geometry.x >= wc_bounds.left)
    & (gsi_dem.geometry.x <= wc_bounds.right)
    & (gsi_dem.geometry.y >= wc_bounds.bottom)
    & (gsi_dem.geometry.y <= wc_bounds.top)
)

print("\nDEM coverage:")
print("Inside:", inside_dem.sum())
print("Outside:", (~inside_dem).sum())

print("\nWorldCover coverage:")
print("Inside:", inside_wc.sum())
print("Outside:", (~inside_wc).sum())

if (~inside_dem).sum() > 0:
    print("\nGSI points outside DEM:")
    print(
        gsi.loc[~inside_dem, ["LATITUDE", "LONGITUDE", "DISTRICT"]]
        .to_string(index=False)
    )

if (~inside_wc).sum() > 0:
    print("\nGSI points outside WorldCover:")
    print(
        gsi.loc[~inside_wc, ["LATITUDE", "LONGITUDE", "DISTRICT"]]
        .to_string(index=False)
    )

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)