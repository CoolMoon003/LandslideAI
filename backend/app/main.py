from __future__ import annotations

import math
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image

from .config import *


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="LandslideAI API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HELPERS
# ============================================================

def exists(p: Path) -> bool:
    return p.exists()


@lru_cache(maxsize=1)
def landslides():
    if not exists(LANDSLIDES):
        return gpd.GeoDataFrame(geometry=[])

    return gpd.read_file(LANDSLIDES)


@lru_cache(maxsize=1)
def roads():
    if not exists(ROADS):
        return gpd.GeoDataFrame(geometry=[])

    return gpd.read_file(ROADS)


@lru_cache(maxsize=1)
def settlements():
    if not exists(SETTLEMENTS):
        return gpd.GeoDataFrame(geometry=[])

    return gpd.read_file(SETTLEMENTS)


@lru_cache(maxsize=1)
def metrics():
    if not exists(MODEL_METRICS):
        return pd.DataFrame()

    return pd.read_csv(MODEL_METRICS)


@lru_cache(maxsize=1)
def rainfall():
    if not exists(RAINFALL):
        return pd.DataFrame()

    df = pd.read_csv(RAINFALL)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce",
        )

    return df


def json_records(df, limit=None):

    if limit:
        df = df.head(limit)

    return (
        df.replace({np.nan: None})
        .to_dict(orient="records")
    )


def risk_category(v):

    if v is None:
        return "NO DATA"

    if isinstance(v, float) and math.isnan(v):
        return "NO DATA"

    v = float(v)

    if v < 0.30:
        return "LOW"

    if v < 0.50:
        return "MODERATE"

    if v < 0.70:
        return "ELEVATED"

    if v < 0.85:
        return "HIGH"

    if v < 0.95:
        return "VERY HIGH"

    return "EXTREME"


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    files = {
        "landslides": LANDSLIDES,
        "model": MODEL,
        "roads": ROADS,
        "settlements": SETTLEMENTS,
        "rainfall": RAINFALL,
        "susceptibility": SUSCEPTIBILITY,
    }

    available = {
        k: exists(v)
        for k, v in files.items()
    }

    return {
        "status": "ok",
        "service": "LandslideAI Risk Engine",
        "files": available,
    }


# ============================================================
# SUMMARY
# ============================================================

@app.get("/api/summary")
def summary(
    date: str = "2022-06-21",
):

    ls = landslides()
    rd = roads()
    st = settlements()
    r = rainfall()

    raster = scenario_raster(date)

    high_plus = None

    if raster.exists():

        with rasterio.open(raster) as src:

            arr = src.read(
                1,
                out_shape=(
                    1,
                    max(1, src.height // 20),
                    max(1, src.width // 20),
                ),
                masked=True,
            )

            a = np.asarray(
                arr,
                dtype="float32",
            )

            high_plus = (
                float(np.mean(a >= 0.70))
                if a.size
                else None
            )

    rain_row = None

    if (
        not r.empty
        and "date" in r.columns
    ):

        x = r[
            r.date.dt.strftime("%Y-%m-%d")
            == date
        ]

        if not x.empty:

            rain_cols = [
                "rainfall_1d",
                "rainfall_3d",
                "rainfall_7d",
                "rainfall_15d",
                "rainfall_30d",
                "trigger_score",
                "risk_category",
            ]

            rain_cols = [
                c for c in rain_cols
                if c in x.columns
            ]

            rain_row = {
                c: (
                    None
                    if pd.isna(x.iloc[0][c])
                    else x.iloc[0][c]
                )
                for c in rain_cols
            }

    return {
        "scenario_date": date,
        "historical_landslides": int(len(ls)),
        "roads": int(len(rd)),
        "settlements": int(len(st)),
        "high_plus_risk_fraction": high_plus,
        "rainfall": rain_row,
        "risk_raster_available": raster.exists(),
    }


# ============================================================
# RISK STATISTICS
# ============================================================

@app.get("/api/risk/statistics")
def risk_statistics(
    date: str = "2022-06-21",
):

    p = scenario_raster(date)

    if not p.exists():
        raise HTTPException(
            404,
            f"No risk raster for {date}",
        )

    with rasterio.open(p) as src:

        a = src.read(
            1,
            out_shape=(
                1,
                max(1, src.height // 10),
                max(1, src.width // 10),
            ),
            masked=True,
        )

        vals = np.asarray(
            a.compressed(),
            dtype="float32",
        )

    if vals.size == 0:

        return {
            "date": date,
            "count": 0,
        }

    return {
        "date": date,
        "count": int(vals.size),
        "mean": float(vals.mean()),
        "min": float(vals.min()),
        "max": float(vals.max()),
        "p25": float(np.percentile(vals, 25)),
        "p50": float(np.percentile(vals, 50)),
        "p75": float(np.percentile(vals, 75)),
        "p90": float(np.percentile(vals, 90)),
        "p95": float(np.percentile(vals, 95)),
        "p99": float(np.percentile(vals, 99)),
    }


# ============================================================
# POINT RISK
# ============================================================

@app.get("/api/risk/point")
def risk_point(
    lat: float,
    lon: float,
    date: str = "2022-06-21",
):

    p = scenario_raster(date)

    if not p.exists():

        raise HTTPException(
            404,
            f"No risk raster for {date}",
        )

    with rasterio.open(p) as src:

        if not (
            src.bounds.left <= lon <= src.bounds.right
            and
            src.bounds.bottom <= lat <= src.bounds.top
        ):

            return {
                "lat": lat,
                "lon": lon,
                "date": date,
                "risk": None,
                "category": "NO DATA",
            }

        value = next(
            src.sample([(lon, lat)])
        )[0]

        if (
            src.nodata is not None
            and value == src.nodata
        ):
            value = None
        else:
            value = float(value)

    return {
        "lat": lat,
        "lon": lon,
        "date": date,
        "risk": value,
        "category": risk_category(value),
    }


# ============================================================
# RISK SCENARIO
# ============================================================

@app.get("/api/risk/scenario")
def risk_scenario(
    date: str = "2022-06-21",
):

    p = scenario_raster(date)

    if not p.exists():

        raise HTTPException(
            404,
            f"No dynamic risk raster for {date}",
        )

    with rasterio.open(p) as src:

        return {
            "date": date,
            "width": src.width,
            "height": src.height,
            "bounds": list(src.bounds),
            "crs": str(src.crs),
            "url": (
                f"/api/risk/overlay"
                f"?date={date}"
            ),
        }


# ============================================================
# RISK OVERLAY
#
# IMPORTANT:
# This endpoint generates the visual PNG.
#
# The underlying model raster is NOT changed.
#
# Visualization:
#
# LOW       -> nearly transparent / dark
# MODERATE  -> yellow
# ELEVATED  -> orange
# HIGH      -> orange-red
# VERY HIGH -> red
# EXTREME   -> deep red
#
# This avoids the previous giant red heatmap effect.
# ============================================================

@app.get("/api/risk/overlay")
def risk_overlay(
    date: str = "2022-06-21",
    max_size: int = Query(
        1400,
        ge=300,
        le=2000,
    ),
):

    p = scenario_raster(date)

    if not p.exists():

        raise HTTPException(
            404,
            f"No dynamic risk raster for {date}",
        )

    with rasterio.open(p) as src:

        # ----------------------------------------------------
        # Resize raster for browser performance
        # ----------------------------------------------------

        scale = max(
            src.width / max_size,
            src.height / max_size,
            1,
        )

        out_w = max(
            1,
            int(src.width / scale),
        )

        out_h = max(
            1,
            int(src.height / scale),
        )

        raster = src.read(
            1,
            out_shape=(
                out_h,
                out_w,
            ),
            masked=True,
        ).astype("float32")

        data = np.ma.filled(
            raster,
            np.nan,
        )

    # --------------------------------------------------------
    # Prepare RGBA image
    # --------------------------------------------------------

    rgba = np.zeros(
        (
            out_h,
            out_w,
            4,
        ),
        dtype=np.uint8,
    )

    valid = np.isfinite(data)

    # --------------------------------------------------------
    # Risk classes
    #
    # We deliberately use discrete classes rather than
    # continuous interpolation.
    # --------------------------------------------------------

    low = (
        valid
        & (data < 0.30)
    )

    moderate = (
        valid
        & (data >= 0.30)
        & (data < 0.50)
    )

    elevated = (
        valid
        & (data >= 0.50)
        & (data < 0.70)
    )

    high = (
        valid
        & (data >= 0.70)
        & (data < 0.85)
    )

    very_high = (
        valid
        & (data >= 0.85)
        & (data < 0.95)
    )

    extreme = (
        valid
        & (data >= 0.95)
    )

    # --------------------------------------------------------
    # COLORS
    #
    # RGB values:
    #
    # LOW       = dark green
    # MODERATE  = yellow
    # ELEVATED  = orange
    # HIGH      = orange-red
    # VERY HIGH = red
    # EXTREME   = deep red
    # --------------------------------------------------------

    # LOW
    rgba[low, 0] = 40
    rgba[low, 1] = 130
    rgba[low, 2] = 85

    # MODERATE
    rgba[moderate, 0] = 235
    rgba[moderate, 1] = 205
    rgba[moderate, 2] = 55

    # ELEVATED
    rgba[elevated, 0] = 245
    rgba[elevated, 1] = 155
    rgba[elevated, 2] = 35

    # HIGH
    rgba[high, 0] = 245
    rgba[high, 1] = 90
    rgba[high, 2] = 35

    # VERY HIGH
    rgba[very_high, 0] = 225
    rgba[very_high, 1] = 40
    rgba[very_high, 2] = 35

    # EXTREME
    rgba[extreme, 0] = 145
    rgba[extreme, 1] = 10
    rgba[extreme, 2] = 20

    # --------------------------------------------------------
    # TRANSPARENCY
    #
    # LOW is almost invisible.
    # Higher risk becomes progressively stronger.
    #
    # This is the important part that prevents the whole
    # Meghalaya map from becoming a red sheet.
    # --------------------------------------------------------

    rgba[low, 3] = 18

    rgba[moderate, 3] = 85

    rgba[elevated, 3] = 120

    rgba[high, 3] = 155

    rgba[very_high, 3] = 185

    rgba[extreme, 3] = 215

    # --------------------------------------------------------
    # Export PNG
    # --------------------------------------------------------

    bio = BytesIO()

    Image.fromarray(
        rgba,
        "RGBA",
    ).save(
        bio,
        format="PNG",
        optimize=True,
    )

    return Response(
        content=bio.getvalue(),
        media_type="image/png",
        headers={
            "Cache-Control": (
                "public, max-age=300"
            )
        },
    )


# ============================================================
# HISTORICAL LANDSLIDES
# ============================================================

@app.get("/api/landslides")
def landslide_points(
    limit: int = Query(
        3000,
        ge=1,
        le=10000,
    ),
):

    g = landslides()

    if g.empty:

        return {
            "type": "FeatureCollection",
            "features": [],
        }

    g = g.to_crs(4326)

    g = g.head(limit)

    return g.to_json()


# ============================================================
# ROADS
# ============================================================

@app.get("/api/infrastructure/roads")
def road_data(
    limit: int = Query(
        5000,
        ge=1,
        le=20000,
    ),
):

    g = roads()

    if g.empty:

        return {
            "type": "FeatureCollection",
            "features": [],
        }

    return (
        g.to_crs(4326)
        .head(limit)
        .to_json()
    )


# ============================================================
# SETTLEMENTS
# ============================================================

@app.get("/api/infrastructure/settlements")
def settlement_data(
    limit: int = Query(
        2000,
        ge=1,
        le=5000,
    ),
):

    g = settlements()

    if g.empty:

        return {
            "type": "FeatureCollection",
            "features": [],
        }

    return (
        g.to_crs(4326)
        .head(limit)
        .to_json()
    )


# ============================================================
# MODEL METRICS
# ============================================================

@app.get("/api/model/metrics")
def model_metrics():
    path = PROCESSED_DATA_DIR / "model_benchmark.csv"

    if not path.exists():
        path = PROCESSED_DATA_DIR / "model_metrics.csv"

    if not path.exists():
        return []

    return pd.read_csv(path).fillna(0).to_dict(orient="records")


# ============================================================
# MODEL FEATURE IMPORTANCE
# ============================================================

@app.get("/api/model/features")
def model_features():

    if not MODEL.exists():
        return {"features": [], "error": "model_file_not_found"}

    try:
        import joblib

        model = joblib.load(MODEL)

        # The saved object may be a bare RandomForestClassifier, or it may be
        # wrapped in a Pipeline/GridSearchCV — unwrap until we find something
        # that actually exposes feature_importances_.
        candidate = model
        for _ in range(4):
            if hasattr(candidate, "feature_importances_"):
                break
            if hasattr(candidate, "best_estimator_"):
                candidate = candidate.best_estimator_
                continue
            if hasattr(candidate, "named_steps"):
                # last step of a Pipeline is almost always the estimator
                candidate = list(candidate.named_steps.values())[-1]
                continue
            if hasattr(candidate, "steps"):
                candidate = candidate.steps[-1][1]
                continue
            break

        imps = getattr(candidate, "feature_importances_", None)

        if imps is None:
            return {
                "features": [],
                "error": "model_has_no_feature_importances",
            }

        # Prefer the names sklearn stored at fit time (set automatically
        # when the model was trained on a DataFrame) — this is the only
        # source that's guaranteed to match the importances' actual order.
        names = getattr(candidate, "feature_names_in_", None)

        if names is None and STATIC_FEATURES.exists():
            try:
                cols = list(pd.read_csv(STATIC_FEATURES, nrows=0).columns)
                drop = {"label", "target", "class", "landslide", "id", "geometry"}
                cols = [c for c in cols if c.lower() not in drop]
                if len(cols) == len(imps):
                    names = cols
            except Exception:
                pass

        if names is None or len(names) != len(imps):
            # Last-resort fallback — order is not verified against the
            # actual training columns, so flag it in the response.
            names = ["elevation", "slope", "aspect", "curvature", "landcover"][: len(imps)]
            return {
                "features": [
                    {"feature": n, "importance": float(v)}
                    for n, v in zip(names, imps)
                ],
                "warning": "feature_names_unverified_fallback_order",
            }

        return {
            "features": [
                {"feature": str(n), "importance": float(v)}
                for n, v in zip(names, imps)
            ]
        }

    except Exception as exc:
        # Surface the real cause instead of silently returning an empty
        # list — this was the actual bug: a bare `except: pass` was
        # hiding whatever went wrong (unpickle error, wrapped estimator,
        # missing dependency, etc).
        return {"features": [], "error": f"{type(exc).__name__}: {exc}"}


# ============================================================
# RISK DISTRIBUTION
# ============================================================

@app.get("/api/risk/distribution")
def risk_distribution(
    date: str = "2022-06-21",
):

    p = scenario_raster(date)

    if not p.exists():

        raise HTTPException(
            404,
            f"No dynamic risk raster for {date}",
        )

    with rasterio.open(p) as src:

        a = src.read(
            1,
            out_shape=(
                1,
                max(1, src.height // 4),
                max(1, src.width // 4),
            ),
            masked=True,
        )

        vals = np.asarray(
            a.compressed(),
            dtype="float32",
        )

    if vals.size == 0:

        return {
            "date": date,
            "total": 0,
            "classes": [],
        }

    bounds = [
        (
            "LOW",
            -np.inf,
            0.30,
        ),
        (
            "MODERATE",
            0.30,
            0.50,
        ),
        (
            "ELEVATED",
            0.50,
            0.70,
        ),
        (
            "HIGH",
            0.70,
            0.85,
        ),
        (
            "VERY HIGH",
            0.85,
            0.95,
        ),
        (
            "EXTREME",
            0.95,
            np.inf,
        ),
    ]

    total = int(vals.size)

    classes = []

    for name, lo, hi in bounds:

        count = int(
            np.sum(
                (vals >= lo)
                & (vals < hi)
            )
        )

        classes.append(
            {
                "class": name,
                "count": count,
                "pct": round(
                    100 * count / total,
                    2,
                )
                if total
                else 0,
            }
        )

    return {
        "date": date,
        "total": total,
        "classes": classes,
    }


# ============================================================
# RAINFALL SCENARIO
# ============================================================

@app.get("/api/rainfall/scenario")
def rainfall_scenario(
    date: str = "2022-06-21",
):

    r = rainfall()

    if (
        r.empty
        or "date" not in r.columns
    ):

        return {
            "date": date,
            "cells": [],
        }

    x = r[
        r.date.dt.strftime("%Y-%m-%d")
        == date
    ].copy()

    return {
        "date": date,
        "cells": json_records(x),
    }