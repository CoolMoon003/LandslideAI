from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


BASE_DIR = Path(__file__).resolve().parents[1]

RAINFALL_DIR = BASE_DIR / "data" / "raw" / "rainfall"

OUTPUT_DIR = BASE_DIR / "data" / "processed"

OUTPUT_FILE = (
    OUTPUT_DIR / "rainfall_meghalaya_summary.csv"
)


# Meghalaya study area
MIN_LON = 89.7
MAX_LON = 92.8
MIN_LAT = 25.0
MAX_LAT = 26.15


def main():

    print("=" * 70)
    print("YHACK LANDSLIDE AI - FULL RAINFALL ANALYSIS")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. Find all rainfall files
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

    print("\n[2] Processing all years...")

    yearly_data = []

    for file in nc_files:

        print(f"\nProcessing: {file.name}")

        with xr.open_dataset(file) as ds:

            rainfall = ds["RAINFALL"]

            lats = ds["LATITUDE"].values

            if lats[0] < lats[-1]:

                lat_slice = slice(
                    MIN_LAT,
                    MAX_LAT
                )

            else:

                lat_slice = slice(
                    MAX_LAT,
                    MIN_LAT
                )

            meghalaya = rainfall.sel(
                LATITUDE=lat_slice,
                LONGITUDE=slice(
                    MIN_LON,
                    MAX_LON
                )
            )

            print(
                f"  Grid: "
                f"{meghalaya.sizes['LATITUDE']} x "
                f"{meghalaya.sizes['LONGITUDE']}"
            )

            # Daily Meghalaya-wide mean
            daily_mean = meghalaya.mean(
                dim=[
                    "LATITUDE",
                    "LONGITUDE"
                ],
                skipna=True
            )

            # Daily Meghalaya-wide maximum
            daily_max = meghalaya.max(
                dim=[
                    "LATITUDE",
                    "LONGITUDE"
                ],
                skipna=True
            )

            year_df = pd.DataFrame(
                {
                    "date": pd.to_datetime(
                        daily_mean["TIME"].values
                    ),
                    "rainfall_mean_mm":
                        daily_mean.values,
                    "rainfall_max_mm":
                        daily_max.values,
                }
            )

            yearly_data.append(year_df)

    # --------------------------------------------------------
    # 3. Combine years
    # --------------------------------------------------------

    print("\n[3] Combining yearly datasets...")

    df = pd.concat(
        yearly_data,
        ignore_index=True
    )

    df = df.sort_values(
        "date"
    ).reset_index(drop=True)

    print(
        f"Total days: {len(df)}"
    )

    print(
        f"Date range: "
        f"{df['date'].min().date()} → "
        f"{df['date'].max().date()}"
    )

    # --------------------------------------------------------
    # 4. Check missing values
    # --------------------------------------------------------

    print("\n[4] Checking missing values...")

    print(
        df.isna().sum()
    )

    df = df.dropna(
        subset=["rainfall_mean_mm"]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # 5. Rolling rainfall windows
    # --------------------------------------------------------

    print("\n[5] Calculating rainfall accumulation...")

    df["rainfall_1d"] = (
        df["rainfall_mean_mm"]
    )

    df["rainfall_3d"] = (
        df["rainfall_mean_mm"]
        .rolling(3)
        .sum()
    )

    df["rainfall_7d"] = (
        df["rainfall_mean_mm"]
        .rolling(7)
        .sum()
    )

    df["rainfall_15d"] = (
        df["rainfall_mean_mm"]
        .rolling(15)
        .sum()
    )

    df["rainfall_30d"] = (
        df["rainfall_mean_mm"]
        .rolling(30)
        .sum()
    )

    # --------------------------------------------------------
    # 6. Statistics across ALL years
    # --------------------------------------------------------

    print("\n[6] Calculating multi-year statistics...")

    windows = [
        "rainfall_1d",
        "rainfall_3d",
        "rainfall_7d",
        "rainfall_15d",
        "rainfall_30d",
    ]

    rows = []

    for window in windows:

        series = df[window].dropna()

        rows.append(
            {
                "window": window,
                "count": len(series),
                "mean": series.mean(),
                "std": series.std(),
                "min": series.min(),
                "p50": series.quantile(0.50),
                "p75": series.quantile(0.75),
                "p90": series.quantile(0.90),
                "p95": series.quantile(0.95),
                "p99": series.quantile(0.99),
                "max": series.max(),
            }
        )

    stats_df = pd.DataFrame(rows)

    print("\nMulti-year rainfall statistics:")
    print(
        stats_df.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 7. Strong rainfall periods
    # --------------------------------------------------------

    print("\n[7] Strongest rainfall periods...")

    top = (
        df.sort_values(
            "rainfall_7d",
            ascending=False
        )
        .head(15)
    )

    print(
        top[
            [
                "date",
                "rainfall_1d",
                "rainfall_3d",
                "rainfall_7d",
                "rainfall_15d",
                "rainfall_30d",
            ]
        ].to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 8. Annual summary
    # --------------------------------------------------------

    print("\n[8] Annual rainfall summary...")

    df["year"] = df["date"].dt.year

    annual = (
        df.groupby("year")
        .agg(
            mean_daily_rainfall=(
                "rainfall_mean_mm",
                "mean"
            ),
            max_1d_rainfall=(
                "rainfall_1d",
                "max"
            ),
            max_3d_rainfall=(
                "rainfall_3d",
                "max"
            ),
            max_7d_rainfall=(
                "rainfall_7d",
                "max"
            ),
            max_30d_rainfall=(
                "rainfall_30d",
                "max"
            ),
        )
        .reset_index()
    )

    print(
        annual.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 9. Save
    # --------------------------------------------------------

    print("\n[9] Saving full rainfall dataset...")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"\nSaved:\n{OUTPUT_FILE}"
    )

    print("\n" + "=" * 70)
    print("FULL RAINFALL ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()