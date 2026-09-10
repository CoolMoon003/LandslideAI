from pathlib import Path

import pandas as pd
import xarray as xr


BASE_DIR = Path(__file__).resolve().parents[1]

RAINFALL_DIR = BASE_DIR / "data" / "raw" / "rainfall"

TARGET_LAT = 25.50
TARGET_LON = 91.00

TARGET_DATE = pd.Timestamp("2015-08-21")


def main():

    print("=" * 75)
    print("RAINFALL CELL SANITY CHECK")
    print("=" * 75)

    file = RAINFALL_DIR / "RF25_ind2015_rfp25.nc"

    print(f"\nFile: {file.name}")
    print(f"Target cell: {TARGET_LAT}, {TARGET_LON}")
    print(f"Target date: {TARGET_DATE.date()}")

    with xr.open_dataset(file) as ds:

        rainfall = ds["RAINFALL"]

        # Select nearest rainfall grid cell
        cell = rainfall.sel(
            LATITUDE=TARGET_LAT,
            LONGITUDE=TARGET_LON,
            method="nearest"
        )

        actual_lat = float(cell["LATITUDE"].values)
        actual_lon = float(cell["LONGITUDE"].values)

        print("\nActual nearest grid cell:")
        print(f"  Latitude : {actual_lat}")
        print(f"  Longitude: {actual_lon}")

        # Convert to pandas series
        series = cell.to_series()

        series.index = pd.to_datetime(series.index)

        # ----------------------------------------------------
        # Show rainfall around target date
        # ----------------------------------------------------

        start_date = TARGET_DATE - pd.Timedelta(days=10)
        end_date = TARGET_DATE

        window = series.loc[start_date:end_date]

        print("\nDaily rainfall around target date:")
        print("-" * 45)

        for date, value in window.items():
            print(
                f"{date.date()} : {float(value):.3f} mm"
            )

        # ----------------------------------------------------
        # Calculate rolling values manually
        # ----------------------------------------------------

        value_1d = series.loc[TARGET_DATE]

        value_3d = series.loc[
            TARGET_DATE - pd.Timedelta(days=2):
            TARGET_DATE
        ].sum()

        value_7d = series.loc[
            TARGET_DATE - pd.Timedelta(days=6):
            TARGET_DATE
        ].sum()

        value_15d = series.loc[
            TARGET_DATE - pd.Timedelta(days=14):
            TARGET_DATE
        ].sum()

        value_30d = series.loc[
            TARGET_DATE - pd.Timedelta(days=29):
            TARGET_DATE
        ].sum()

        print("\nCalculated accumulations:")
        print("-" * 45)

        print(f"1-day  : {float(value_1d):.3f} mm")
        print(f"3-day  : {float(value_3d):.3f} mm")
        print(f"7-day  : {float(value_7d):.3f} mm")
        print(f"15-day : {float(value_15d):.3f} mm")
        print(f"30-day : {float(value_30d):.3f} mm")

        # ----------------------------------------------------
        # Check dataset metadata
        # ----------------------------------------------------

        print("\nRainfall variable information:")
        print("-" * 45)

        print(rainfall)

        print("\nAttributes:")

        for key, value in rainfall.attrs.items():
            print(f"  {key}: {value}")

    print("\n" + "=" * 75)
    print("SANITY CHECK COMPLETE")
    print("=" * 75)


if __name__ == "__main__":
    main()