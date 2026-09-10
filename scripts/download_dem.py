"""
scripts/download_dem.py

Downloads Copernicus GLO-30 DEM tiles covering the Meghalaya bounding box
directly from the public AWS Open Data bucket 'copernicus-dem-30m'
(https://registry.opendata.aws/copernicus-dem/). This bucket allows
anonymous HTTPS GET requests -- no AWS account, no credentials, no API key.

Mosaics the required 1deg x 1deg tiles and clips to the exact bounding box.
Output: data/raw/dem/meghalaya_dem_30m.tif
"""
import math
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
import requests
from rasterio.merge import merge
from rasterio.windows import from_bounds
from tqdm import tqdm

# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEM_DIR = PROJECT_ROOT / "data" / "raw" / "dem"
TILE_DIR = DEM_DIR / "tiles"
OUTPUT_PATH = DEM_DIR / "meghalaya_dem_30m.tif"

BBOX = {"west": 89.7, "east": 92.8, "south": 25.0, "north": 26.15}

S3_BASE = "https://copernicus-dem-30m.s3.amazonaws.com"

MAX_RETRIES = 4
TIMEOUT_SECS = 120


def tile_name_and_url(lat: int, lon: int):
    lat_str = f"N{lat:02d}" if lat >= 0 else f"S{abs(lat):02d}"
    lon_str = f"E{lon:03d}" if lon >= 0 else f"W{abs(lon):03d}"
    tile = f"Copernicus_DSM_COG_10_{lat_str}_00_{lon_str}_00_DEM"
    url = f"{S3_BASE}/{tile}/{tile}.tif"
    return tile, url


def required_tiles(bbox: dict):
    eps = 1e-9
    lat_start = int(math.floor(bbox["south"]))
    lat_end = int(math.floor(bbox["north"] - eps))
    lon_start = int(math.floor(bbox["west"]))
    lon_end = int(math.floor(bbox["east"] - eps))
    tiles = []
    for lat in range(lat_start, lat_end + 1):
        for lon in range(lon_start, lon_end + 1):
            tiles.append((lat, lon))
    return tiles


def download_tile(url: str, out_path: Path) -> bool:
    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"  [skip] {out_path.name} already exists")
        return True

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with requests.get(url, stream=True, timeout=TIMEOUT_SECS) as resp:
                if resp.status_code == 404:
                    print(f"  [error] Tile not found at {url} (404) -- this "
                          f"1x1 deg cell may not have GLO-30 public coverage.")
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
    print("Mosaicking tiles...")
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
    DEM_DIR.mkdir(parents=True, exist_ok=True)

    if OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0:
        print(f"Output already exists: {OUTPUT_PATH} -- skipping full re-run.")
        print("Delete the file if you want to force a fresh download/mosaic.")
    else:
        tiles = required_tiles(BBOX)
        print(f"Meghalaya bbox requires {len(tiles)} Copernicus GLO-30 tile(s): {tiles}")

        tile_paths = []
        for lat, lon in tiles:
            tile_name, url = tile_name_and_url(lat, lon)
            out_path = TILE_DIR / f"{tile_name}.tif"
            print(f"Fetching {tile_name} ...")
            ok = download_tile(url, out_path)
            if ok and out_path.exists():
                tile_paths.append(out_path)

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

    print("\nDEM DOWNLOAD COMPLETE")
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