from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import xy
from scipy.ndimage import gaussian_filter
from tqdm import tqdm


ROOT = Path(__file__).resolve().parents[1]

DEM_PATH = ROOT / "data" / "raw" / "dem" / "meghalaya_dem_30m.tif"
OUTPUT_DIR = ROOT / "data" / "processed" / "terrain"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


print("=" * 70)
print("YHACK LANDSLIDE AI - TERRAIN FEATURE GENERATION")
print("=" * 70)


# ---------------------------------------------------------
# READ DEM
# ---------------------------------------------------------

print("\n[1] Reading DEM...")

with rasterio.open(DEM_PATH) as src:
    dem = src.read(1).astype(np.float32)
    profile = src.profile.copy()
    transform = src.transform
    crs = src.crs
    resolution = src.res

print("DEM shape:", dem.shape)
print("Resolution:", resolution)
print("CRS:", crs)


# ---------------------------------------------------------
# HANDLE INVALID VALUES
# ---------------------------------------------------------

print("\n[2] Cleaning DEM...")

invalid = ~np.isfinite(dem)

if invalid.any():
    print("Invalid pixels:", invalid.sum())

    valid_values = dem[~invalid]

    replacement = np.median(valid_values)

    dem[invalid] = replacement
else:
    print("No invalid values found.")


# ---------------------------------------------------------
# CONVERT DEGREE RESOLUTION TO METERS
# ---------------------------------------------------------

# DEM is EPSG:4326.
# Approximate conversion at Meghalaya latitude.

mean_lat = 25.5

meters_per_degree_lat = 111320.0
meters_per_degree_lon = 111320.0 * np.cos(np.radians(mean_lat))

pixel_size_x = abs(resolution[0]) * meters_per_degree_lon
pixel_size_y = abs(resolution[1]) * meters_per_degree_lat

print("\nApproximate pixel size:")
print("X:", round(pixel_size_x, 2), "meters")
print("Y:", round(pixel_size_y, 2), "meters")


# ---------------------------------------------------------
# SMOOTH DEM SLIGHTLY
# ---------------------------------------------------------

# A very small smoothing reduces single-pixel noise
# before calculating derivatives.

print("\n[3] Preparing DEM...")

dem_smooth = gaussian_filter(dem, sigma=1)


# ---------------------------------------------------------
# SLOPE + ASPECT
# ---------------------------------------------------------

print("\n[4] Calculating slope and aspect...")

dz_dy, dz_dx = np.gradient(
    dem_smooth,
    pixel_size_y,
    pixel_size_x
)

slope_rad = np.arctan(
    np.sqrt(dz_dx ** 2 + dz_dy ** 2)
)

slope_deg = np.degrees(slope_rad)

# Aspect convention:
# 0 = North
# 90 = East
# 180 = South
# 270 = West

aspect_rad = np.arctan2(-dz_dx, dz_dy)

aspect_deg = np.degrees(aspect_rad)

aspect_deg = np.where(
    aspect_deg < 0,
    aspect_deg + 360,
    aspect_deg
)


# ---------------------------------------------------------
# CURVATURE
# ---------------------------------------------------------

print("\n[5] Calculating curvature...")

d2z_dx2 = np.gradient(dz_dx, pixel_size_x, axis=1)
d2z_dy2 = np.gradient(dz_dy, pixel_size_y, axis=0)

curvature = d2z_dx2 + d2z_dy2


# ---------------------------------------------------------
# WRITE FUNCTION
# ---------------------------------------------------------

def save_raster(data, filename):
    output_path = OUTPUT_DIR / filename

    output_profile = profile.copy()

    output_profile.update(
        dtype="float32",
        count=1,
        compress="deflate",
        predictor=2,
        nodata=np.nan
    )

    with rasterio.open(output_path, "w", **output_profile) as dst:
        dst.write(data.astype(np.float32), 1)

    print("Saved:", output_path)


# ---------------------------------------------------------
# SAVE FEATURES
# ---------------------------------------------------------

print("\n[6] Saving terrain rasters...")

save_raster(dem, "elevation.tif")
save_raster(slope_deg, "slope.tif")
save_raster(aspect_deg, "aspect.tif")
save_raster(curvature, "curvature.tif")


# ---------------------------------------------------------
# STATISTICS
# ---------------------------------------------------------

print("\n[7] Feature statistics")

features = {
    "Elevation": dem,
    "Slope": slope_deg,
    "Aspect": aspect_deg,
    "Curvature": curvature,
}

for name, data in features.items():

    valid = data[np.isfinite(data)]

    print(
        f"{name:12s} | "
        f"min={np.percentile(valid, 1):.3f} | "
        f"median={np.median(valid):.3f} | "
        f"max={np.percentile(valid, 99):.3f}"
    )


print("\n" + "=" * 70)
print("TERRAIN FEATURE GENERATION COMPLETE")
print("=" * 70)