from pathlib import Path
import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GSI_PATH = ROOT / "data" / "raw" / "landslides" / "GSI_Landslide_Inventory.geojson"

print("=" * 70)
print("MEGHALAYA GSI DETAILED INSPECTION")
print("=" * 70)

gsi = gpd.read_file(GSI_PATH)

# ---------------------------------------------------------
# FILTER MEGHALAYA
# ---------------------------------------------------------

meghalaya = gsi[
    gsi["STATE"]
    .astype(str)
    .str.strip()
    .str.lower()
    == "meghalaya"
].copy()

print("\nTotal Meghalaya landslides:", len(meghalaya))

# ---------------------------------------------------------
# INITIATION YEAR
# ---------------------------------------------------------

print("\n" + "-" * 60)
print("INITIATION YEAR")
print("-" * 60)

print(meghalaya["INITIATION"].value_counts().sort_index())

valid_years = meghalaya[
    pd.to_numeric(meghalaya["INITIATION"], errors="coerce").between(1900, 2025)
]

print("\nRecords with valid year:", len(valid_years))
print("Records with unknown/invalid year:", len(meghalaya) - len(valid_years))

if len(valid_years) > 0:
    print("\nValid year distribution:")
    print(valid_years["INITIATION"].value_counts().sort_index())

# ---------------------------------------------------------
# TRIGGERING
# ---------------------------------------------------------

print("\n" + "-" * 60)
print("TRIGGERING")
print("-" * 60)

print(meghalaya["TRIGGERING"].fillna("").astype(str).str.strip().value_counts().head(40))

# ---------------------------------------------------------
# LAND USE / LAND COVER
# ---------------------------------------------------------

print("\n" + "-" * 60)
print("LANDUSE / LANDCOVER")
print("-" * 60)

if "LANDUSE_LANDCOVER" in meghalaya.columns:
    print(
        meghalaya["LANDUSE_LANDCOVER"]
        .fillna("")
        .astype(str)
        .str.strip()
        .value_counts()
        .head(30)
    )

# ---------------------------------------------------------
# GEOLOGY
# ---------------------------------------------------------

print("\n" + "-" * 60)
print("GEOLOGY")
print("-" * 60)

print(
    meghalaya["GEOLOGY"]
    .fillna("")
    .astype(str)
    .str.strip()
    .value_counts()
    .head(30)
)

# ---------------------------------------------------------
# MOVEMENT TYPE
# ---------------------------------------------------------

print("\n" + "-" * 60)
print("MOVEMENT TYPE")
print("-" * 60)

print(
    meghalaya["MOVEMENT_TYPE"]
    .fillna("")
    .astype(str)
    .str.strip()
    .value_counts()
    .head(20)
)

# ---------------------------------------------------------
# INFRASTRUCTURE IMPACT
# ---------------------------------------------------------

print("\n" + "-" * 60)
print("INFRASTRUCTURE AFFECTED")
print("-" * 60)

print(
    meghalaya["INFRASTRUCTURE_AFFECTED"]
    .fillna("")
    .astype(str)
    .str.strip()
    .value_counts()
    .head(30)
)

# ---------------------------------------------------------
# COMMUNICATION AFFECTED
# ---------------------------------------------------------

print("\n" + "-" * 60)
print("COMMUNICATION AFFECTED")
print("-" * 60)

print(
    meghalaya["COMMUNICATION_AFFECTED"]
    .fillna("")
    .astype(str)
    .str.strip()
    .value_counts()
    .head(20)
)

# ---------------------------------------------------------
# COORDINATES
# ---------------------------------------------------------

print("\n" + "-" * 60)
print("COORDINATES")
print("-" * 60)

print("Longitude:")
print("  min:", meghalaya["LONGITUDE"].min())
print("  max:", meghalaya["LONGITUDE"].max())

print("Latitude:")
print("  min:", meghalaya["LATITUDE"].min())
print("  max:", meghalaya["LATITUDE"].max())

# ---------------------------------------------------------
# MISSING VALUES
# ---------------------------------------------------------

print("\n" + "-" * 60)
print("IMPORTANT MISSING VALUES")
print("-" * 60)

for col in [
    "INITIATION",
    "TRIGGERING",
    "GEOLOGY",
    "LANDUSE_LANDCOVER",
    "INFRASTRUCTURE_AFFECTED",
]:
    if col in meghalaya.columns:
        missing = (
            meghalaya[col].isna()
            | meghalaya[col].astype(str).str.strip().eq("")
        ).sum()

        print(f"{col}: {missing}/{len(meghalaya)} missing/blank")

# ---------------------------------------------------------
# SAVE CLEAN MEGHALAYA FILE
# ---------------------------------------------------------

output = ROOT / "data" / "processed" / "meghalaya_landslides.geojson"
output.parent.mkdir(parents=True, exist_ok=True)

meghalaya.to_file(output, driver="GeoJSON")

print("\nSaved:")
print(output)

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)