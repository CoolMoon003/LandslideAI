"""
scripts/download_worldcover.py

Downloads ESA WorldCover 2021 v200 (10m land cover) tiles covering the
Meghalaya bounding box, directly from the official public AWS S3 bucket
(https://registry.opendata.aws/esa-worldcover-vito/). Anonymous HTTPS GET --
no AWS account, no credentials, no API key.

Uses the official ESA WorldCover tile grid (published as a GeoJSON on the
same public bucket) to determine which tiles intersect the bounding box --
same approach as ESA's own download helper script
(https://github.com/ESA-WorldCover/esa-worldcover-datasets).

Output tiles: data/raw/landcover/tiles/
Mosaic:       data/raw/landcover/meghalaya_worldcover_2021_10m.tif
"""
import sys
import time
from pathlib import Path

import geopandas as gpd
import rasterio
import requests
from rasterio.merge import merge
from rasterio.windows import from_bounds
from shapely.geometry import box
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LC_DIR = PROJECT_ROOT / "data" / "raw" / "landcover"
TILE_DIR = LC_DIR / "tiles"
OUTPUT_PATH = LC_DIR / "meghalaya_worldcover_2021_10m.tif"

BBOX = {"west": 89.7, "east": 92.8, "south": 25.0, "north": 26.15}

S3_PREFIX = "https://esa-worldcover.s3.eu-central-1.amazonaws.com"
GRID_URL = f"{S3_PREFIX}/v100/2020/esa_worldcover_2020_grid.geojson"

YEAR = 2021
VERSION = {2020: "v100", 2021: "v200"}[YEAR]

MAX_RETRIES = 4
TIMEOUT_SECS = 300


def download_file(url: str, out_path: Path) -> bool:
    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"  [skip] {out_path.name} already exists")
        return True

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with requests.get(url, stream=True, timeout=TIMEOUT_SECS) as resp:
                if resp.status_code == 404:
                    print(f"  [error] Tile not found (404): {url}")
                    return False
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                tmp_path = out_path.with_suffix(".tmp")
                with open(tmp_path, "wb") as f, tqdm(
                    total=total, unit="B", unit_scale=True,
                    desc=f"  {out_path.name}", leave=False,
                ) as bar:
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                            bar.update(len(chunk))
                tmp_path.rename(out_path)
            return True
        except (requests.RequestException, IOError) as e:
            wait = 2 ** attempt
            print(f"  [retry {attempt}/{MAX_RETRIES}] {e} -- waiting {wait}s")
            time.sleep(wait)
    print(f"  [FAILED] Could not download {url} after {MAX_RETRIES} attempts")
    return False


def mosaic_and_clip(tile_paths, bbox, output_path):
    print("Mosaicking WorldCover tiles...")
    datasets = [rasterio.open(p) for p in tile_paths]
    mosaic_arr, mosaic_transform = merge(datasets)
    src_crs = datasets[0].crs
    for ds in datasets:
        ds.close()

    print("Clipping to Meghalaya bounding box...")
    window = from_bounds(
        bbox["west"], bbox["south"], bbox["east"], bbox["north"],
        transform=mosaic_transform,
    )
    window = window.round_lengths().round_offsets()
    col_off, row_off = int(window.col_off), int(window.row_off)
    width, height = int(window.width), int(window.height)

    col_off = max(col_off, 0)
    row_off = max(row_off, 0)
    width = min(width, mosaic_arr.shape[2] - col_off)
    height = min(height, mosaic_arr.shape[1] - row_off)

    clipped = mosaic_arr[:, row_off:row_off + height, col_off:col_off + width]
    clipped_transform = rasterio.windows.transform(
        rasterio.windows.Window(col_off, row_off, width, height), mosaic_transform
    )

    profile = {
        "driver": "GTiff",
        "height": clipped.shape[1],
        "width": clipped.shape[2],
        "count": clipped.shape[0],
        "dtype": clipped.dtype,
        "crs": src_crs,
        "transform": clipped_transform,
        "compress": "deflate",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(clipped)


def main():
    TILE_DIR.mkdir(parents=True, exist_ok=True)
    LC_DIR.mkdir(parents=True, exist_ok=True)

    if OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0:
        print(f"Output already exists: {OUTPUT_PATH} -- skipping full re-run.")
        downloaded_tiles = ["(reused existing mosaic)"]
    else:
        print("Loading official ESA WorldCover tile grid...")
        grid = gpd.read_file(GRID_URL)
        aoi = box(BBOX["west"], BBOX["south"], BBOX["east"], BBOX["north"])
        tiles = grid[grid.intersects(aoi)]

        if len(tiles) == 0:
            print("ERROR: no WorldCover tiles intersect the given bounding box.",
                  file=sys.stderr)
            sys.exit(1)

        print(f"Meghalaya bbox requires {len(tiles)} WorldCover tile(s): "
              f"{list(tiles.ll_tile)}")

        tile_paths = []
        downloaded_tiles = []
        for tile_id in tiles.ll_tile:
            url = (f"{S3_PREFIX}/{VERSION}/{YEAR}/map/"
                   f"ESA_WorldCover_10m_{YEAR}_{VERSION}_{tile_id}_Map.tif")
            out_path = TILE_DIR / f"ESA_WorldCover_10m_{YEAR}_{VERSION}_{tile_id}_Map.tif"
            print(f"Fetching tile {tile_id} ...")
            ok = download_file(url, out_path)
            if ok and out_path.exists():
                tile_paths.append(out_path)
                downloaded_tiles.append(tile_id)

        if not tile_paths:
            print("ERROR: no tiles downloaded successfully. Aborting.", file=sys.stderr)
            sys.exit(1)

        mosaic_and_clip(tile_paths, BBOX, OUTPUT_PATH)

    with rasterio.open(OUTPUT_PATH) as ds:
        crs = ds.crs
        res = ds.res
        width, height = ds.width, ds.height
        bounds = ds.bounds
    size_mb = OUTPUT_PATH.stat().st_size / 1e6

    print("\nWORLDCOVER DOWNLOAD COMPLETE")
    print(f"Downloaded tiles: {downloaded_tiles}")
    print("Output:")
    print(f"  {OUTPUT_PATH.resolve()}")
    print(f"CRS: {crs}")
    print(f"Resolution: {res}")
    print(f"Width: {width}")
    print(f"Height: {height}")
    print(f"Bounds: {bounds}")
    print(f"File size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()