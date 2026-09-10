from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ============================================================
# DATA DIRECTORIES
# ============================================================

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Lightweight files committed for deployment
DEPLOYMENT_DATA_DIR = PROJECT_ROOT / "deployment_data"

# ============================================================
# RISK RASTERS
# ============================================================

DEPLOYMENT_RISK_DIR = DEPLOYMENT_DATA_DIR / "risk"
RISK_DIR = PROCESSED_DATA_DIR / "risk"

# Prefer lightweight deployment files when available.
# Otherwise use the original local processed files.

def deployment_or_local(deployment_path: Path, local_path: Path) -> Path:
    return deployment_path if deployment_path.exists() else local_path


SUSCEPTIBILITY = deployment_or_local(
    DEPLOYMENT_RISK_DIR / "susceptibility_30m.tif",
    RISK_DIR / "susceptibility_30m.tif",
)

DYNAMIC_RISK = deployment_or_local(
    DEPLOYMENT_RISK_DIR / "dynamic_risk_2022-06-21.tif",
    RISK_DIR / "dynamic_risk_2022-06-21.tif",
)

RAINFALL_TRIGGER = deployment_or_local(
    DEPLOYMENT_RISK_DIR / "rainfall_trigger_2022-06-21.tif",
    RISK_DIR / "rainfall_trigger_2022-06-21.tif",
)

RISK_CLASS = deployment_or_local(
    DEPLOYMENT_RISK_DIR / "risk_class_2022-06-21.tif",
    RISK_DIR / "risk_class_2022-06-21.tif",
)

# ============================================================
# ORIGINAL TERRAIN RASTERS
# ============================================================

ELEVATION = PROCESSED_DATA_DIR / "elevation.tif"
SLOPE = PROCESSED_DATA_DIR / "slope.tif"
ASPECT = PROCESSED_DATA_DIR / "aspect.tif"
CURVATURE = PROCESSED_DATA_DIR / "curvature.tif"

# ============================================================
# MODELS
# ============================================================

MODELS_DIR = PROJECT_ROOT / "models"

MODEL = MODELS_DIR / "random_forest_static.joblib"
LOGISTIC_MODEL = MODELS_DIR / "logistic_regression_static.joblib"

# ============================================================
# VECTOR DATA
# ============================================================

LANDSLIDES = PROCESSED_DATA_DIR / "meghalaya_landslides.geojson"

DEPLOYMENT_INFRA_DIR = DEPLOYMENT_DATA_DIR / "infrastructure"

DEPLOYMENT_ROADS = (
    DEPLOYMENT_INFRA_DIR / "roads_risk_analysis.geojson"
)

PROCESSED_ROADS = (
    PROCESSED_DATA_DIR
    / "infrastructure"
    / "roads_risk_analysis.geojson"
)

RAW_ROADS = RAW_DATA_DIR / "osm" / "roads.geojson"

ROADS = (
    DEPLOYMENT_ROADS
    if DEPLOYMENT_ROADS.exists()
    else (
        PROCESSED_ROADS
        if PROCESSED_ROADS.exists()
        else RAW_ROADS
    )
)


DEPLOYMENT_SETTLEMENTS = (
    DEPLOYMENT_INFRA_DIR / "settlements_risk_analysis.geojson"
)

PROCESSED_SETTLEMENTS = (
    PROCESSED_DATA_DIR
    / "infrastructure"
    / "settlements_risk_analysis.geojson"
)

RAW_SETTLEMENTS = RAW_DATA_DIR / "osm" / "settlements.geojson"

SETTLEMENTS = (
    DEPLOYMENT_SETTLEMENTS
    if DEPLOYMENT_SETTLEMENTS.exists()
    else (
        PROCESSED_SETTLEMENTS
        if PROCESSED_SETTLEMENTS.exists()
        else RAW_SETTLEMENTS
    )
)

# ============================================================
# PROCESSED TABLES
# ============================================================

STATIC_FEATURES = PROCESSED_DATA_DIR / "meghalaya_static_features.csv"

TRAINING_STATIC = PROCESSED_DATA_DIR / "meghalaya_training_static.csv"

MODEL_METRICS = PROCESSED_DATA_DIR / "model_metrics.csv"

RAINFALL_SUMMARY = (
    PROCESSED_DATA_DIR / "rainfall_meghalaya_summary.csv"
)

RAINFALL_SPATIAL = (
    PROCESSED_DATA_DIR
    / "rainfall"
    / "meghalaya_rainfall_spatial.csv"
)

RAINFALL = (
    RAINFALL_SUMMARY
    if RAINFALL_SUMMARY.exists()
    else (
        RAINFALL_SPATIAL
        if RAINFALL_SPATIAL.exists()
        else PROCESSED_DATA_DIR / "meghalaya_rainfall_spatial.csv"
    )
)

# ============================================================
# DEFAULT SCENARIO
# ============================================================

DEFAULT_DATE = "2022-06-21"

# ============================================================
# MEGHALAYA MAP CENTER
# ============================================================

MEGHALAYA_CENTER_LAT = 25.4670
MEGHALAYA_CENTER_LON = 91.3662

# ============================================================
# SCENARIO RASTER RESOLVER
# ============================================================

def scenario_raster(date: str) -> Path:
    """
    Return the dynamic-risk raster for a requested scenario date.
    Prefer deployment raster when available.
    """

    deployment_candidate = (
        DEPLOYMENT_RISK_DIR
        / f"dynamic_risk_{date}.tif"
    )

    if deployment_candidate.exists():
        return deployment_candidate

    local_candidate = (
        RISK_DIR
        / f"dynamic_risk_{date}.tif"
    )

    if local_candidate.exists():
        return local_candidate

    if date == DEFAULT_DATE and DYNAMIC_RISK.exists():
        return DYNAMIC_RISK

    return local_candidate