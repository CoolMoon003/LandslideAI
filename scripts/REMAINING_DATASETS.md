# Remaining Datasets — LandslideAI (Meghalaya / NER)
You already have: `GSI_Landslide_Inventory.geojson` and IMD rainfall (2015–2025, one file/year).
Below are the other four inputs your architecture doc calls for, each verified live and matched with a ready-to-run script in `scripts/`.

---

## 1. DEM (Elevation / Slope / Aspect)
**Source used:** OpenTopography Global DEM API — covers both SRTM GL1 (30m) and Copernicus DSM (COP30/COP90), one HTTP GET, no manual tiling.

- Get a free instant API key: https://portal.opentopography.org/myopentopo
- Script: `scripts/fetch_dem_opentopography.py`
  - Set `demtype = "COP30"` for Copernicus DEM (matches your doc's "Copernicus DEM / SRTM" line, generally more current/accurate over forested hill terrain) or `"SRTMGL1"` for classic 30m SRTM.
  - Bounding box is pre-set to Meghalaya; NER-wide box is included as a comment.
  - Also derives slope (degrees) and aspect (degrees) as separate GeoTIFFs.

No login beyond the free API key. One call, ~50–150MB for Meghalaya at 30m.

---

## 2. Land Cover
**Source used:** ESA WorldCover 10m (2021, v200) — public AWS S3 bucket, no login, no AWS account needed.

- Bucket root: `https://esa-worldcover.s3.eu-central-1.amazonaws.com`
- Tile grid (to find which 3°×3° tiles cover your area): `https://esa-worldcover.s3.eu-central-1.amazonaws.com/v100/2020/esa_worldcover_2020_grid.geojson`
- Script: `scripts/fetch_worldcover.py` — pass a bounding box, it reads the grid, finds intersecting tiles, and downloads each tile's `_Map.tif` directly (no AWS CLI, no credentials).
- Classes (11): Tree cover, Shrubland, Grassland, Cropland, Built-up, Bare/sparse vegetation, Snow/Ice, Permanent water, Herbaceous wetland, Mangroves, Moss/lichen — legend baked into the script's `WORLDCOVER_CLASSES` dict.

---

## 3. Soil / Geology
**Source used:** ISRIC SoilGrids v2.0 REST API — point-query, no login. (Global GSI geology maps are not cleanly downloadable, so SoilGrids is the practical substitute your doc marks as "optional enhancement.")

- Endpoint: `https://rest.isric.org/soilgrids/v2.0/properties/query?lon=...&lat=...&property=...&depth=0-5cm&value=mean`
- Useful properties for landslide susceptibility: `clay`, `sand`, `silt` (texture — affects permeability/shear strength), `bdod` (bulk density), `soc` (organic carbon), `cec`.
- Script: `scripts/fetch_soilgrids.py` — takes your landslide points (positive samples) + generated background points (negative samples) and queries SoilGrids for each, writing a joined CSV. Respects the API's fair-use limit (5 calls/minute) with built-in throttling.
- This is the slowest part of the pipeline (rate-limited) — run it early, in the background, while you work on DEM/land cover.

---

## 4. Roads, Settlements, Buildings
**Source used:** OpenStreetMap via the public Overpass API — no login.

- Script: `scripts/fetch_osm_meghalaya.py` — pulls roads (trunk/primary/secondary/tertiary), villages/hamlets, schools, hospitals, and building footprints for Meghalaya (easily edited to loop over other NER states — the list is at the top of the file).
- Output: one GeoJSON per layer (`meghalaya_roads.geojson`, `meghalaya_villages.geojson`, `meghalaya_schools.geojson`, `meghalaya_hospitals.geojson`, `meghalaya_buildings.geojson`).
- Note: the `buildings` query can return a lot of features in dense towns — the script caps it with a `[timeout:180]` and per-request bbox chunking isn't included by default; if Overpass times out, shrink to a district-level bbox.

---

## Run order
```bash
pip install -r requirements.txt

export OPENTOPOGRAPHY_API_KEY=your_key_here
python scripts/fetch_dem_opentopography.py

python scripts/fetch_worldcover.py

python scripts/fetch_osm_meghalaya.py

python scripts/fetch_soilgrids.py   # slowest — start this first if running in parallel terminals
```

After these four finish, you'll have every layer listed in Section 6 of your architecture doc (GSI ✅ already have, IMD rainfall ✅ already have, DEM ✅, ESA WorldCover ✅, OSM ✅, SoilGrids ✅) and can move straight to Section 7 (the feature-extraction pipeline) — `scripts/build_grid_features.py` from the earlier kit is the join skeleton for that step.
