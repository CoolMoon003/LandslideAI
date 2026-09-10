"""
YHACK LANDSLIDE AI
Static Landslide Susceptibility Model Training

Models:
1. Logistic Regression - baseline
2. Random Forest - primary model

Validation:
Spatial/block-aware split using geographic grid cells.

Output:
    models/random_forest_static.joblib
    models/logistic_regression_static.joblib
    data/processed/model_metrics.csv
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "meghalaya_training_static.csv"
)

MODEL_DIR = BASE_DIR / "models"

RF_MODEL_FILE = (
    MODEL_DIR / "random_forest_static.joblib"
)

LR_MODEL_FILE = (
    MODEL_DIR / "logistic_regression_static.joblib"
)

METRICS_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "model_metrics.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_STATE = 42

# Spatial grid size in degrees.
# Approximately 5-10 km depending on latitude.
GRID_SIZE = 0.05

FEATURES = [
    "elevation",
    "slope",
    "aspect",
    "curvature",
    "landcover_class",
]

TARGET = "label"


# ============================================================
# SPATIAL SPLIT
# ============================================================

def create_spatial_split(df):
    """
    Create a geographic block-based train/test split.

    Points belonging to the same geographic grid cell stay
    together, reducing spatial leakage.
    """

    print("\n[3] Creating spatial/block split...")

    df = df.copy()

    # Create geographic grid IDs
    df["grid_x"] = np.floor(
        df["longitude"] / GRID_SIZE
    )

    df["grid_y"] = np.floor(
        df["latitude"] / GRID_SIZE
    )

    df["grid_id"] = (
        df["grid_x"].astype(str)
        + "_"
        + df["grid_y"].astype(str)
    )

    unique_grids = df["grid_id"].unique()

    rng = np.random.default_rng(RANDOM_STATE)

    rng.shuffle(unique_grids)

    # Approximately 80% of geographic blocks for training
    split_index = int(len(unique_grids) * 0.80)

    train_grids = unique_grids[:split_index]
    test_grids = unique_grids[split_index:]

    train_mask = df["grid_id"].isin(train_grids)
    test_mask = df["grid_id"].isin(test_grids)

    train_df = df[train_mask].copy()
    test_df = df[test_mask].copy()

    # Remove helper columns
    train_df = train_df.drop(
        columns=["grid_x", "grid_y", "grid_id"]
    )

    test_df = test_df.drop(
        columns=["grid_x", "grid_y", "grid_id"]
    )

    print(f"Total geographic blocks: {len(unique_grids)}")
    print(f"Training blocks: {len(train_grids)}")
    print(f"Testing blocks: {len(test_grids)}")

    print(f"\nTraining samples: {len(train_df)}")
    print(f"Testing samples: {len(test_df)}")

    print("\nTraining class distribution:")
    print(train_df[TARGET].value_counts())

    print("\nTesting class distribution:")
    print(test_df[TARGET].value_counts())

    return train_df, test_df


# ============================================================
# EVALUATION
# ============================================================

def evaluate_model(name, model, X_test, y_test):

    print("\n" + "=" * 70)
    print(f"{name.upper()} RESULTS")
    print("=" * 70)

    predictions = model.predict(X_test)

    probabilities = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(
        y_test,
        predictions
    )

    precision = precision_score(
        y_test,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        y_test,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0
    )

    roc_auc = roc_auc_score(
        y_test,
        probabilities
    )

    pr_auc = average_precision_score(
        y_test,
        probabilities
    )

    cm = confusion_matrix(
        y_test,
        predictions
    )

    print(f"Accuracy : {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1 Score : {f1:.4f}")
    print(f"ROC-AUC  : {roc_auc:.4f}")
    print(f"PR-AUC   : {pr_auc:.4f}")

    print("\nConfusion Matrix:")
    print(cm)

    return {
        "model": name,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("YHACK LANDSLIDE AI - STATIC MODEL TRAINING")
    print("=" * 70)

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # 1. Load dataset
    # --------------------------------------------------------

    print("\n[1] Loading training dataset...")

    df = pd.read_csv(DATA_FILE)

    print(f"Dataset shape: {df.shape}")

    print("\nColumns:")
    print(list(df.columns))

    # --------------------------------------------------------
    # 2. Validate data
    # --------------------------------------------------------

    print("\n[2] Checking dataset...")

    missing = df[
        FEATURES + [TARGET]
    ].isna().sum()

    print("\nMissing values:")
    print(missing)

    if missing.sum() > 0:

        print(
            "\nRemoving rows with missing model features..."
        )

        df = df.dropna(
            subset=FEATURES + [TARGET]
        ).reset_index(drop=True)

    print(
        f"\nFinal samples: {len(df)}"
    )

    # --------------------------------------------------------
    # 3. Spatial split
    # --------------------------------------------------------

    train_df, test_df = create_spatial_split(df)

    # --------------------------------------------------------
    # 4. Prepare X/y
    # --------------------------------------------------------

    print("\n[4] Preparing features and labels...")

    X_train = train_df[FEATURES]
    y_train = train_df[TARGET]

    X_test = test_df[FEATURES]
    y_test = test_df[TARGET]

    print("\nFeatures used:")

    for feature in FEATURES:
        print(f"  - {feature}")

    # --------------------------------------------------------
    # 5. Logistic Regression
    # --------------------------------------------------------

    print("\n[5] Training Logistic Regression...")

    logistic_model = Pipeline(
        [
            (
                "scaler",
                StandardScaler()
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2000,
                    random_state=RANDOM_STATE
                )
            ),
        ]
    )

    logistic_model.fit(
        X_train,
        y_train
    )

    lr_metrics = evaluate_model(
        "Logistic Regression",
        logistic_model,
        X_test,
        y_test
    )

    # --------------------------------------------------------
    # 6. Random Forest
    # --------------------------------------------------------

    print("\n[6] Training Random Forest...")

    random_forest = RandomForestClassifier(
        n_estimators=400,
        max_depth=18,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    random_forest.fit(
        X_train,
        y_train
    )

    rf_metrics = evaluate_model(
        "Random Forest",
        random_forest,
        X_test,
        y_test
    )

    # --------------------------------------------------------
    # 7. Feature importance
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("RANDOM FOREST FEATURE IMPORTANCE")
    print("=" * 70)

    importance_df = pd.DataFrame(
        {
            "feature": FEATURES,
            "importance": random_forest.feature_importances_,
        }
    ).sort_values(
        "importance",
        ascending=False
    )

    print(
        importance_df.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 8. Compare models
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("MODEL COMPARISON")
    print("=" * 70)

    metrics_df = pd.DataFrame(
        [
            lr_metrics,
            rf_metrics,
        ]
    )

    print(
        metrics_df.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 9. Save models
    # --------------------------------------------------------

    print("\n[7] Saving models...")

    joblib.dump(
        random_forest,
        RF_MODEL_FILE
    )

    joblib.dump(
        logistic_model,
        LR_MODEL_FILE
    )

    print(
        f"Random Forest saved:\n{RF_MODEL_FILE}"
    )

    print(
        f"Logistic Regression saved:\n{LR_MODEL_FILE}"
    )

    # --------------------------------------------------------
    # 10. Save metrics
    # --------------------------------------------------------

    metrics_df.to_csv(
        METRICS_FILE,
        index=False
    )

    print(
        f"\nMetrics saved:\n{METRICS_FILE}"
    )

    # --------------------------------------------------------
    # 11. Final recommendation
    # --------------------------------------------------------

    best_model = metrics_df.loc[
        metrics_df["f1"].idxmax(),
        "model"
    ]

    print("\n" + "=" * 70)
    print("BEST MODEL")
    print("=" * 70)

    print(
        f"Based on F1 score: {best_model}"
    )

    print("\n" + "=" * 70)
    print("STATIC MODEL TRAINING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()