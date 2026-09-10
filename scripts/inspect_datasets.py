from pathlib import Path
import geopandas as gpd
import rasterio
import xarray as xr
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

print("=" * 70)
print("YHACK LANDSLIDE AI - DATASET INSPECTION")
print("=" * 70)

# ---------------------------------------------------------
# 1. GSI LANDSLIDES
# ---------------------------------------------------------
print("\n[1] GSI LANDSLIDE INVENTORY")
print("-" * 50)

gsi_path = RAW / "landslides" / "GSI_Landslide_Inventory.geojson"

gsi = gpd.read_file(gsi_path)

print("Total records:", len(gsi))
print("CRS:", gsi.crs)
print("Geometry types:")
print(gsi.geometry.geom_type.value_counts())

print("\nColumns:")
print(list(gsi.columns))

if "STATE" in gsi.columns:
    print("\nTop states:")
    print(gsi["STATE"].value_counts().head(15))

    meghalaya = gsi[
        gsi["STATE"]
        .astype(str)
        .str.strip()
        .str.lower()
        == "meghalaya"
    ]

    print("\nMeghalaya records:", len(meghalaya))

    if len(meghalaya) > 0:
        print("\nMeghalaya districts:")
        if "DISTRICT" in meghalaya.columns:
            print(meghalaya["DISTRICT"].value_counts())

if "INITIATION" in gsi.columns:
    print("\nINITIATION values:")
    print(gsi["INITIATION"].value_counts().head(20))

if "TRIGGERING" in gsi.columns:
    print("\nTRIGGERING values:")
    print(gsi["TRIGGERING"].value_counts().head(20))

print("\nSample record:")
print(gsi.head(2).to_string())


# ---------------------------------------------------------
# 2. RAINFALL
# ---------------------------------------------------------
print("\n\n[2] RAINFALL NETCDF")
print("-" * 50)

rainfall_dir = RAW / "rainfall"
nc_files = sorted(rainfall_dir.glob("*.nc"))

print("NetCDF files found:", len(nc_files))

if nc_files:
    rainfall_path = nc_files[0]

    print("Inspecting:", rainfall_path.name)

    ds = xr.open_dataset(rainfall_path)

    print("\nDimensions:")
    print(ds.dims)

    print("\nCoordinates:")
    for name in ds.coords:
        coord = ds[name]
        print(
            f"  {name}: shape={coord.shape}, "
            f"min={coord.values.min()}, max={coord.values.max()}"
        )

    print("\nVariables:")
    for name in ds.data_vars:
        var = ds[name]
        print(f"  {name}")
        print("    dimensions:", var.dims)
        print("    shape:", var.shape)
        print("    dtype:", var.dtype)
        print("    attributes:", dict(var.attrs))

    if "TIME" in ds:
        print("\nTime:")
        print("Start:", ds["TIME"].values[0])
        print("End:", ds["TIME"].values[-1])

    ds.close()


# ---------------------------------------------------------
# 3. DEM
# ---------------------------------------------------------
print("\n\n[3] DEM")
print("-" * 50)

dem_path = RAW / "dem" / "meghalaya_dem_30m.tif"

with rasterio.open(dem_path) as src:
    print("CRS:", src.crs)
    print("Width:", src.width)
    print("Height:", src.height)
    print("Bands:", src.count)
    print("Resolution:", src.res)
    print("Bounds:", src.bounds)
    print("NoData:", src.nodata)

    sample = src.read(1, masked=True)

    print("Elevation min:", float(sample.min()))
    print("Elevation max:", float(sample.max()))


# ---------------------------------------------------------
# 4. WORLDCOVER
# ---------------------------------------------------------
print("\n\n[4] ESA WORLDCOVER")
print("-" * 50)

wc_path = RAW / "landcover" / "meghalaya_worldcover_2021_10m.tif"

with rasterio.open(wc_path) as src:
    print("CRS:", src.crs)
    print("Width:", src.width)
    print("Height:", src.height)
    print("Bands:", src.count)
    print("Resolution:", src.res)
    print("Bounds:", src.bounds)
    print("NoData:", src.nodata)

    data = src.read(1, masked=True)

    print("\nWorldCover classes:")
    values, counts = pd.Series(data.compressed()).value_counts().sort_index().index, \
                     pd.Series(data.compressed()).value_counts().sort_index().values

    for value, count in zip(values, counts):
        print(f"  Class {value}: {count:,} pixels")


# ---------------------------------------------------------
# 5. OSM ROADS
# ---------------------------------------------------------
print("\n\n[5] OSM ROADS")
print("-" * 50)

roads_path = RAW / "osm" / "roads.geojson"

roads = gpd.read_file(roads_path)

print("Road features:", len(roads))
print("CRS:", roads.crs)
print("Geometry types:")
print(roads.geometry.geom_type.value_counts())

print("\nColumns:")
print(list(roads.columns))


# ---------------------------------------------------------
# 6. OSM SETTLEMENTS
# ---------------------------------------------------------
print("\n\n[6] OSM SETTLEMENTS")
print("-" * 50)

settlements_path = RAW / "osm" / "settlements.geojson"

settlements = gpd.read_file(settlements_path)

print("Settlement features:", len(settlements))
print("CRS:", settlements.crs)
print("Geometry types:")
print(settlements.geometry.geom_type.value_counts())

print("\nColumns:")
print(list(settlements.columns))


# ---------------------------------------------------------
# DONE
# ---------------------------------------------------------
print("\n" + "=" * 70)
print("INSPECTION COMPLETE")
print("=" * 70)