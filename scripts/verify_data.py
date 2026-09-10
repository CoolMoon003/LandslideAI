"""
scripts/verify_data.py
"""
import json
from pathlib import Path

import rasterio

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RASTER_FILES = [
    PROJECT_ROOT / "data" / "raw" / "dem" / "meghalaya_dem_30m.tif",
    PROJECT_ROOT / "data" / "raw" / "landcover" / "meghalaya_worldcover_2021_10m.tif",
]

VECTOR_FILES = [
    PROJECT_ROOT / "data" / "raw" / "osm" / "roads.geojson",
    PROJECT_ROOT / "data" / "raw" / "osm" / "settlements.geojson",
]


def report_raster(path: Path):
    print(f"\n{path.name}")
    if not path.exists():
        print("  MISSING")
        return
    size_mb = path.stat().st_size / 1e6
    with rasterio.open(path) as ds:
        print(f"  Path:       {path.resolve()}")
        print(f"  Size:       {size_mb:.2f} MB")
        print(f"  CRS:        {ds.crs}")
        print(f"  Resolution: {ds.res}")
        print(f"  Dimensions: {ds.width} x {ds.height}")
        print(f"  Bounds:     {ds.bounds}")


def report_vector(path: Path):
    print(f"\n{path.name}")
    if not path.exists():
        print("  MISSING")
        return
    size_mb = path.stat().st_size / 1e6
    with open(path) as f:
        data = json.load(f)
    n_features = len(data.get("features", []))
    print(f"  Path:            {path.resolve()}")
    print(f"  Size:            {size_mb:.2f} MB")
    print(f"  Feature count:   {n_features}")


def main():
    print("=" * 60)
    print("DATA VERIFICATION REPORT")
    print("=" * 60)

    for p in RASTER_FILES:
        report_raster(p)

    for p in VECTOR_FILES:
        report_vector(p)

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()