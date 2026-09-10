from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

RAINFALL_DIR = BASE_DIR / "data" / "raw" / "rainfall"
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "rainfall"

OUTPUT_FILE = OUTPUT_DIR / "meghalaya_rainfall_spatial.csv"


# ============================================================
# MEGHALAYA BOUNDS
# ============================================================

MIN_LON = 89.7
MAX_LON = 92.8

MIN_LAT = 25.0
MAX_LAT = 26.15


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 75)
    print("YHACK LANDSLIDE AI - SPATIAL RAINFALL FEATURES")
    print("=" * 75)

    # --------------------------------------------------------
    # 1. Find NetCDF files
    # --------------------------------------------------------

    print("\n[1] Finding rainfall files...")

    nc_files = sorted(
        RAINFALL_DIR.glob("RF25_ind*_rfp25.nc")
    )

    if not nc_files:
        raise FileNotFoundError(
            f"No rainfall files found in {RAINFALL_DIR}"
        )

    print(f"Files found: {len(nc_files)}")

    for file in nc_files:
        print(f"  - {file.name}")

    # --------------------------------------------------------
    # 2. Process every year
    # --------------------------------------------------------

    print("\n[2] Processing rainfall grids...")

    all_years = []

    for file in nc_files:

        print(f"\nProcessing: {file.name}")

        with xr.open_dataset(file) as ds:

            rainfall = ds["RAINFALL"]

            # Check latitude direction
            lats = ds["LATITUDE"].values

            if lats[0] < lats[-1]:
                lat_slice = slice(MIN_LAT, MAX_LAT)
            else:
                lat_slice = slice(MAX_LAT, MIN_LAT)

            # Meghalaya subset
            meghalaya = rainfall.sel(
                LATITUDE=lat_slice,
                LONGITUDE=slice(MIN_LON, MAX_LON)
            )

            print(
                f"  Grid: "
                f"{meghalaya.sizes['LATITUDE']} x "
                f"{meghalaya.sizes['LONGITUDE']}"
            )

            # ------------------------------------------------
            # Convert to dataframe
            # ------------------------------------------------

            temp = meghalaya.to_dataframe(
                name="rainfall_mm"
            ).reset_index()

            temp = temp.rename(
                columns={
                    "TIME": "date",
                    "LATITUDE": "latitude",
                    "LONGITUDE": "longitude",
                }
            )

            temp["date"] = pd.to_datetime(temp["date"])

            all_years.append(
                temp[
                    [
                        "date",
                        "latitude",
                        "longitude",
                        "rainfall_mm",
                    ]
                ]
            )

    # --------------------------------------------------------
    # 3. Combine all years
    # --------------------------------------------------------

    print("\n[3] Combining all years...")

    df = pd.concat(
        all_years,
        ignore_index=True
    )

    df = df.sort_values(
        ["latitude", "longitude", "date"]
    ).reset_index(drop=True)

    print(f"Total rows: {len(df):,}")

    print(
        f"Date range: "
        f"{df['date'].min().date()} → "
        f"{df['date'].max().date()}"
    )

    print(
        f"Unique rainfall cells: "
        f"{df[['latitude', 'longitude']].drop_duplicates().shape[0]}"
    )

    # --------------------------------------------------------
    # 4. Calculate rolling rainfall
    # --------------------------------------------------------

    print("\n[4] Calculating rainfall accumulation...")

    grouped = df.groupby(
        ["latitude", "longitude"],
        group_keys=False
    )

    df["rainfall_1d"] = df["rainfall_mm"]

    df["rainfall_3d"] = grouped["rainfall_mm"].transform(
        lambda x: x.rolling(3, min_periods=3).sum()
    )

    df["rainfall_7d"] = grouped["rainfall_mm"].transform(
        lambda x: x.rolling(7, min_periods=7).sum()
    )

    df["rainfall_15d"] = grouped["rainfall_mm"].transform(
        lambda x: x.rolling(15, min_periods=15).sum()
    )

    df["rainfall_30d"] = grouped["rainfall_mm"].transform(
        lambda x: x.rolling(30, min_periods=30).sum()
    )

    # --------------------------------------------------------
    # 5. Calculate percentile thresholds
    # --------------------------------------------------------

    print("\n[5] Calculating rainfall percentiles...")

    windows = [
        "rainfall_1d",
        "rainfall_3d",
        "rainfall_7d",
        "rainfall_15d",
        "rainfall_30d",
    ]

    percentile_values = {}

    for window in windows:

        series = df[window].dropna()

        percentile_values[window] = {
            "p50": series.quantile(0.50),
            "p75": series.quantile(0.75),
            "p90": series.quantile(0.90),
            "p95": series.quantile(0.95),
            "p99": series.quantile(0.99),
        }

        print(
            f"\n{window}:"
            f"\n  P50 = {percentile_values[window]['p50']:.2f}"
            f"\n  P75 = {percentile_values[window]['p75']:.2f}"
            f"\n  P90 = {percentile_values[window]['p90']:.2f}"
            f"\n  P95 = {percentile_values[window]['p95']:.2f}"
            f"\n  P99 = {percentile_values[window]['p99']:.2f}"
        )

    # --------------------------------------------------------
    # 6. Convert rainfall to percentile-based scores
    # --------------------------------------------------------

    print("\n[6] Creating rainfall trigger scores...")

    def percentile_score(value, thresholds):

        if pd.isna(value):
            return np.nan

        if value <= thresholds["p50"]:
            return 0.10

        elif value <= thresholds["p75"]:
            return 0.30

        elif value <= thresholds["p90"]:
            return 0.50

        elif value <= thresholds["p95"]:
            return 0.70

        elif value <= thresholds["p99"]:
            return 0.90

        else:
            return 1.00

    for window in windows:

        score_column = window + "_score"

        thresholds = percentile_values[window]

        df[score_column] = df[window].apply(
            lambda x: percentile_score(
                x,
                thresholds
            )
        )

    # --------------------------------------------------------
    # 7. Combined rainfall trigger
    # --------------------------------------------------------

    print("\n[7] Creating combined rainfall trigger...")

    df["rainfall_trigger"] = (
        0.15 * df["rainfall_1d_score"]
        + 0.15 * df["rainfall_3d_score"]
        + 0.30 * df["rainfall_7d_score"]
        + 0.20 * df["rainfall_15d_score"]
        + 0.20 * df["rainfall_30d_score"]
    )

    # --------------------------------------------------------
    # 8. Assign rainfall risk category
    # --------------------------------------------------------

    def risk_category(score):

        if score < 0.30:
            return "LOW"

        elif score < 0.50:
            return "MODERATE"

        elif score < 0.70:
            return "ELEVATED"

        elif score < 0.85:
            return "HIGH"

        elif score < 0.95:
            return "VERY HIGH"

        else:
            return "EXTREME"

    df["rainfall_risk"] = df["rainfall_trigger"].apply(
        risk_category
    )

    # --------------------------------------------------------
    # 9. Keep useful columns
    # --------------------------------------------------------

    df = df[
        [
            "date",
            "latitude",
            "longitude",

            "rainfall_1d",
            "rainfall_3d",
            "rainfall_7d",
            "rainfall_15d",
            "rainfall_30d",

            "rainfall_1d_score",
            "rainfall_3d_score",
            "rainfall_7d_score",
            "rainfall_15d_score",
            "rainfall_30d_score",

            "rainfall_trigger",
            "rainfall_risk",
        ]
    ]

    # --------------------------------------------------------
    # 10. Display strongest rainfall events
    # --------------------------------------------------------

    print("\n[8] Strongest rainfall situations...")

    strongest = (
        df.sort_values(
            "rainfall_trigger",
            ascending=False
        )
        .head(20)
    )

    print(
        strongest[
            [
                "date",
                "latitude",
                "longitude",
                "rainfall_7d",
                "rainfall_30d",
                "rainfall_trigger",
                "rainfall_risk",
            ]
        ].to_string(index=False)
    )

    # --------------------------------------------------------
    # 11. Risk distribution
    # --------------------------------------------------------

    print("\n[9] Rainfall risk distribution...")

    print(
        df["rainfall_risk"]
        .value_counts()
        .sort_index()
    )

    # --------------------------------------------------------
    # 12. Save
    # --------------------------------------------------------

    print("\n[10] Saving spatial rainfall dataset...")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\nSaved:")
    print(OUTPUT_FILE)

    print("\n" + "=" * 75)
    print("SPATIAL RAINFALL FEATURE GENERATION COMPLETE")
    print("=" * 75)


if __name__ == "__main__":
    main()