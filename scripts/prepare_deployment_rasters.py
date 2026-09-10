from pathlib import Path
import rasterio
from rasterio.enums import Resampling

ROOT = Path(__file__).resolve().parents[1]

INPUTS = {
    "susceptibility_30m.tif": ROOT / "data/processed/risk/susceptibility_30m.tif",
    "dynamic_risk_2022-06-21.tif": ROOT / "data/processed/risk/dynamic_risk_2022-06-21.tif",
    "rainfall_trigger_2022-06-21.tif": ROOT / "data/processed/risk/rainfall_trigger_2022-06-21.tif",
    "risk_class_2022-06-21.tif": ROOT / "data/processed/risk/risk_class_2022-06-21.tif",
}

OUTPUT_DIR = ROOT / "deployment_data/risk"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SCALE = 4

for name, src_path in INPUTS.items():

    if not src_path.exists():
        print(f"SKIP: {src_path}")
        continue

    output_path = OUTPUT_DIR / name

    # Remove partially-created file from previous failed run
    if output_path.exists():
        output_path.unlink()

    print(f"\nProcessing: {name}")

    with rasterio.open(src_path) as src:

        new_width = max(1, src.width // SCALE)
        new_height = max(1, src.height // SCALE)

        new_transform = src.transform * src.transform.scale(
            src.width / new_width,
            src.height / new_height,
        )

        profile = src.profile.copy()

        # Remove source tiling/block configuration.
        # We'll use a normal compressed TIFF.
        profile.pop("blockxsize", None)
        profile.pop("blockysize", None)

        profile.update(
            driver="GTiff",
            width=new_width,
            height=new_height,
            transform=new_transform,
            compress="deflate",
            predictor=2,
            tiled=False,
            BIGTIFF="IF_SAFER",
        )

        if "class" in name:
            resampling = Resampling.nearest
        else:
            resampling = Resampling.bilinear

        with rasterio.open(output_path, "w", **profile) as dst:

            for band in range(1, src.count + 1):

                data = src.read(
                    band,
                    out_shape=(new_height, new_width),
                    resampling=resampling,
                )

                dst.write(data, band)

        size_mb = output_path.stat().st_size / (1024 * 1024)

        print(f"  Original : {src.width} x {src.height}")
        print(f"  New      : {new_width} x {new_height}")
        print(f"  Size     : {size_mb:.2f} MB")

print("\n================================")
print("Deployment rasters created.")
print("================================")