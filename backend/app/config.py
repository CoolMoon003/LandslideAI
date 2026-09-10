from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Risk rasters are stored in data/processed/risk
RISK_DIR = PROCESSED_DATA_DIR / "risk"

MODELS_DIR = PROJECT_ROOT / "models"


# ============================================================
# RASTER DATA
# ============================================================

ELEVATION = PROCESSED_DATA_DIR / "elevation.tif"
SLOPE = PROCESSED_DATA_DIR / "slope.tif"
ASPECT = PROCESSED_DATA_DIR / "aspect.tif"
CURVATURE = PROCESSED_DATA_DIR / "curvature.tif"

SUSCEPTIBILITY = RISK_DIR / "susceptibility_30m.tif"

DYNAMIC_RISK = RISK_DIR / "dynamic_risk_2022-06-21.tif"
RAINFALL_TRIGGER = RISK_DIR / "rainfall_trigger_2022-06-21.tif"
RISK_CLASS = RISK_DIR / "risk_class_2022-06-21.tif"


# ============================================================
# VECTOR DATA
# ============================================================

LANDSLIDES = PROCESSED_DATA_DIR / "meghalaya_landslides.geojson"

PROCESSED_ROADS = PROCESSED_DATA_DIR / "infrastructure" / "roads_risk_analysis.geojson"
RAW_ROADS = RAW_DATA_DIR / "osm" / "roads.geojson"
ROADS = PROCESSED_ROADS if PROCESSED_ROADS.exists() else RAW_ROADS

PROCESSED_SETTLEMENTS = PROCESSED_DATA_DIR / "infrastructure" / "settlements_risk_analysis.geojson"
RAW_SETTLEMENTS = RAW_DATA_DIR / "osm" / "settlements.geojson"
SETTLEMENTS = PROCESSED_SETTLEMENTS if PROCESSED_SETTLEMENTS.exists() else RAW_SETTLEMENTS


# ============================================================
# PROCESSED TABLES
# ============================================================

STATIC_FEATURES = PROCESSED_DATA_DIR / "meghalaya_static_features.csv"

TRAINING_STATIC = PROCESSED_DATA_DIR / "meghalaya_training_static.csv"

MODEL_METRICS = PROCESSED_DATA_DIR / "model_metrics.csv"

RAINFALL_SUMMARY = PROCESSED_DATA_DIR / "rainfall_meghalaya_summary.csv"
RAINFALL_SPATIAL = PROCESSED_DATA_DIR / "rainfall" / "meghalaya_rainfall_spatial.csv"
RAINFALL = RAINFALL_SUMMARY if RAINFALL_SUMMARY.exists() else (
    RAINFALL_SPATIAL if RAINFALL_SPATIAL.exists() else PROCESSED_DATA_DIR / "meghalaya_rainfall_spatial.csv"
)


# ============================================================
# MODELS
# ============================================================

MODEL = MODELS_DIR / "random_forest_static.joblib"

LOGISTIC_MODEL = MODELS_DIR / "logistic_regression_static.joblib"


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
    """

    candidate = RISK_DIR / f"dynamic_risk_{date}.tif"

    if candidate.exists():
        return candidate

    if date == DEFAULT_DATE and DYNAMIC_RISK.exists():
        return DYNAMIC_RISK

    return candidate