"""
scripts/download_osm.py

Downloads roads and settlements for the Meghalaya bounding box from
OpenStreetMap via the public Overpass API -- no login, no API key.

Tries multiple public Overpass mirrors in turn for reliability, with retry
and timeout handling.

Output:
  data/raw/osm/roads.geojson
  data/raw/osm/settlements.geojson
"""
import json
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OSM_DIR = PROJECT_ROOT / "data" / "raw" / "osm"

ROADS_OUT = OSM_DIR / "roads.geojson"
SETTLEMENTS_OUT = OSM_DIR / "settlements.geojson"

BBOX = {"west": 89.7, "east": 92.8, "south": 25.0, "north": 26.15}
# Overpass bbox order is: south,west,north,east
OVERPASS_BBOX = f"{BBOX['south']},{BBOX['west']},{BBOX['north']},{BBOX['east']}"

OVERPASS_MIRRORS = [
    "https://overpass.private.coffee/api/interpreter",   # formerly kumi.systems
    "https://lz4.overpass-api.de/api/interpreter",        # large-query endpoint
    "https://z.overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass-api.de/api/interpreter",            # last resort
]

# overpass-api.de (and some mirrors) now reject requests that look
# non-interactive/bot-like with HTTP 406 unless a real User-Agent is set.
REQUEST_HEADERS = {
    "User-Agent": "YHack-Landslide-AI/1.0 (hackathon project; contact: naveen@example.com)",
    "Accept": "application/json, text/plain, */*",
}

# Keep the server-side Overpass timeout modest so a stuck mirror fails fast
# and we move to the next one, instead of hanging for minutes per attempt.
OVERPASS_SERVER_TIMEOUT = 60
CLIENT_TIMEOUT_SECS = 90
MAX_RETRIES_PER_MIRROR = 1

ROADS_QUERY = f"""
[out:json][timeout:{OVERPASS_SERVER_TIMEOUT}];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified)$"]
     ({OVERPASS_BBOX});
);
out geom;
"""

SETTLEMENTS_QUERY = f"""
[out:json][timeout:{OVERPASS_SERVER_TIMEOUT}];
(
  node["place"~"^(village|hamlet)$"]({OVERPASS_BBOX});
  way["place"~"^(village|hamlet)$"]({OVERPASS_BBOX});
);
out center;
"""


def run_overpass_query(query: str) -> dict:
    last_error = None
    for mirror in OVERPASS_MIRRORS:
        for attempt in range(1, MAX_RETRIES_PER_MIRROR + 1):
            try:
                print(f"  Querying {mirror} (attempt {attempt})...")
                resp = requests.post(
                    mirror, data={"data": query}, headers=REQUEST_HEADERS,
                    timeout=CLIENT_TIMEOUT_SECS,
                )
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, json.JSONDecodeError) as e:
                last_error = e
                print(f"    failed ({e}) -- trying next option")
                time.sleep(2)
    raise RuntimeError(f"All Overpass mirrors failed. Last error: {last_error}")


def overpass_to_geojson(osm_json: dict, geometry_kind: str) -> dict:
    """geometry_kind: 'line' for roads (way geometry), 'point' for settlements."""
    features = []
    for el in osm_json.get("elements", []):
        tags = el.get("tags", {})
        props = {
            "osm_id": el.get("id"),
            "osm_type": el.get("type"),
            "name": tags.get("name"),
            "highway": tags.get("highway"),
            "place": tags.get("place"),
        }

        if el["type"] == "node":
            geom = {"type": "Point", "coordinates": [el["lon"], el["lat"]]}
        elif el["type"] == "way":
            if geometry_kind == "line" and "geometry" in el:
                coords = [[p["lon"], p["lat"]] for p in el["geometry"]]
                geom = {"type": "LineString", "coordinates": coords}
            elif "center" in el:
                geom = {"type": "Point", "coordinates": [el["center"]["lon"], el["center"]["lat"]]}
            else:
                continue
        else:
            continue

        features.append({"type": "Feature", "geometry": geom, "properties": props})

    return {"type": "FeatureCollection", "features": features}


def save_if_needed(out_path: Path, fetch_fn):
    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"[skip] {out_path.name} already exists")
        with open(out_path) as f:
            data = json.load(f)
        return len(data.get("features", []))

    gj = fetch_fn()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(gj, f)
    return len(gj["features"])


def fetch_roads():
    print("Fetching roads (motorway/trunk/primary/secondary/tertiary/unclassified)...")
    osm_json = run_overpass_query(ROADS_QUERY)
    return overpass_to_geojson(osm_json, geometry_kind="line")


def fetch_settlements():
    print("Fetching settlements (village/hamlet)...")
    osm_json = run_overpass_query(SETTLEMENTS_QUERY)
    return overpass_to_geojson(osm_json, geometry_kind="point")


def main():
    OSM_DIR.mkdir(parents=True, exist_ok=True)

    n_roads = save_if_needed(ROADS_OUT, fetch_roads)
    n_settlements = save_if_needed(SETTLEMENTS_OUT, fetch_settlements)

    print("\nOSM DOWNLOAD COMPLETE")
    print(f"Roads features:       {n_roads}  -> {ROADS_OUT.resolve()}")
    print(f"Settlements features: {n_settlements}  -> {SETTLEMENTS_OUT.resolve()}")


if __name__ == "__main__":
    main()