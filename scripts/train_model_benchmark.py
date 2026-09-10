from pathlib import Path
import shutil
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
)

from xgboost import XGBClassifier


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = ROOT / "data" / "processed" / "meghalaya_training_static.csv"
MODEL_DIR = ROOT / "models"
OUTPUT_PATH = ROOT / "data" / "processed" / "model_benchmark.csv"

MODEL_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# CONFIG
# ============================================================

FEATURES = [
    "elevation",
    "slope",
    "aspect",
    "curvature",
    "landcover_class",
]

TARGET = "label"

GRID_SIZE = 0.05
RANDOM_STATE = 42


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("LANDSLIDE ML MODEL BENCHMARK")
print("=" * 70)

print("\nLoading dataset...")

df = pd.read_csv(DATA_PATH)

print(f"Dataset shape: {df.shape}")

X = df[FEATURES].copy()
y = df[TARGET].astype(int)


# ============================================================
# SPATIAL BLOCK SPLIT
# ============================================================

print("\nCreating spatial blocks...")

df["_grid_lat"] = np.floor(df["latitude"] / GRID_SIZE)
df["_grid_lon"] = np.floor(df["longitude"] / GRID_SIZE)

df["_block"] = (
    df["_grid_lat"].astype(str)
    + "_"
    + df["_grid_lon"].astype(str)
)

blocks = df["_block"].unique()

train_blocks, test_blocks = train_test_split(
    blocks,
    test_size=0.20,
    random_state=RANDOM_STATE,
)

train_mask = df["_block"].isin(train_blocks)
test_mask = df["_block"].isin(test_blocks)

X_train = X.loc[train_mask]
X_test = X.loc[test_mask]

y_train = y.loc[train_mask]
y_test = y.loc[test_mask]

print(f"Total geographic blocks : {len(blocks)}")
print(f"Training blocks         : {len(train_blocks)}")
print(f"Testing blocks          : {len(test_blocks)}")

print(f"\nTraining samples: {len(X_train)}")
print(f"Testing samples : {len(X_test)}")

print(
    f"Training labels: {y_train.sum()} positive / "
    f"{len(y_train) - y_train.sum()} negative"
)

print(
    f"Testing labels : {y_test.sum()} positive / "
    f"{len(y_test) - y_test.sum()} negative"
)


# ============================================================
# MODELS
# ============================================================

models = {

    "Logistic Regression": Pipeline([
        (
            "scaler",
            StandardScaler()
        ),
        (
            "model",
            LogisticRegression(
                max_iter=2000,
                random_state=RANDOM_STATE,
            )
        ),
    ]),

    "Random Forest": RandomForestClassifier(
        n_estimators=400,
        max_depth=18,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    ),

    "Gradient Boosting": GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=3,
        random_state=RANDOM_STATE,
    ),

    "XGBoost": XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    ),
}


# ============================================================
# TRAIN + EVALUATE
# ============================================================

results = []
trained_models = {}

print("\n" + "=" * 70)
print("TRAINING MODELS")
print("=" * 70)

for name, model in models.items():

    print(f"\n{'-' * 70}")
    print(f"Training: {name}")
    print(f"{'-' * 70}")

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    if hasattr(model, "predict_proba"):
        y_prob = model.predict_proba(X_test)[:, 1]
    else:
        y_prob = y_pred

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(
        y_test,
        y_pred,
        zero_division=0,
    )
    recall = recall_score(
        y_test,
        y_pred,
        zero_division=0,
    )
    f1 = f1_score(
        y_test,
        y_pred,
        zero_division=0,
    )
    roc_auc = roc_auc_score(
        y_test,
        y_prob,
    )
    pr_auc = average_precision_score(
        y_test,
        y_prob,
    )

    cm = confusion_matrix(
        y_test,
        y_pred,
    )

    print(f"Accuracy : {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1 Score : {f1:.4f}")
    print(f"ROC-AUC  : {roc_auc:.4f}")
    print(f"PR-AUC   : {pr_auc:.4f}")

    print("\nConfusion Matrix:")
    print(cm)

    # --------------------------------------------------------
    # Save individual model
    # --------------------------------------------------------

    filename = (
        name.lower()
        .replace(" ", "_")
        .replace("-", "")
        + "_static.joblib"
    )

    model_path = MODEL_DIR / filename

    joblib.dump(
        model,
        model_path,
    )

    print(f"\nSaved: {model_path}")

    trained_models[name] = model

    results.append({
        "model": name,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "tn": int(cm[0, 0]),
        "fp": int(cm[0, 1]),
        "fn": int(cm[1, 0]),
        "tp": int(cm[1, 1]),
    })


# ============================================================
# RESULTS DATAFRAME
# ============================================================

results_df = pd.DataFrame(results)


# ============================================================
# SELECT BEST MODEL
# ============================================================
#
# Primary metric : F1
# Tie breaker    : PR-AUC
# Tie breaker    : ROC-AUC
#
# This avoids choosing purely on accuracy.
# ============================================================

results_df = results_df.sort_values(
    by=[
        "f1",
        "pr_auc",
        "roc_auc",
    ],
    ascending=False,
).reset_index(drop=True)

results_df["selected"] = False

best_model_name = results_df.loc[0, "model"]

results_df.loc[0, "selected"] = True


# ============================================================
# SAVE BENCHMARK RESULTS
# ============================================================

results_df.to_csv(
    OUTPUT_PATH,
    index=False,
)

print("\n" + "=" * 70)
print("MODEL RANKING")
print("=" * 70)

display_columns = [
    "model",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "roc_auc",
    "pr_auc",
    "selected",
]

print(
    results_df[display_columns]
    .to_string(index=False)
)


# ============================================================
# COPY BEST MODEL TO WEBSITE-COMPATIBLE PATH
# ============================================================
#
# Your existing backend currently expects:
#
# models/random_forest_static.joblib
#
# Instead of changing the frontend/backend every time a different
# model wins, we place the winning model at that path.
#
# The actual model type is still recorded in model_benchmark.csv.
# ============================================================

best_model = trained_models[best_model_name]

selected_model_path = MODEL_DIR / "selected_model.joblib"

joblib.dump(
    best_model,
    selected_model_path,
)

# Compatibility path used by the current backend
website_model_path = MODEL_DIR / "random_forest_static.joblib"

shutil.copy2(
    selected_model_path,
    website_model_path,
)

print("\n" + "=" * 70)
print("SELECTED MODEL")
print("=" * 70)

print(f"🏆 Best model: {best_model_name}")

print(f"\nSaved selected model:")
print(selected_model_path)

print("\nWebsite-compatible model:")
print(website_model_path)


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

print("\n" + "=" * 70)
print("FEATURE IMPORTANCE")
print("=" * 70)

if hasattr(best_model, "feature_importances_"):

    importances = best_model.feature_importances_

    feature_df = pd.DataFrame({
        "feature": FEATURES,
        "importance": importances,
    })

    feature_df = feature_df.sort_values(
        "importance",
        ascending=False,
    )

    print(
        feature_df.to_string(index=False)
    )

    feature_df.to_csv(
        ROOT
        / "data"
        / "processed"
        / "selected_model_features.csv",
        index=False,
    )

else:

    print(
        "Selected model does not expose feature_importances_."
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

best_row = results_df.iloc[0]

print("\n" + "=" * 70)
print("FINAL RESULT")
print("=" * 70)

print(f"""
🏆 Selected Model : {best_model_name}

Accuracy         : {best_row["accuracy"]:.2%}
Precision        : {best_row["precision"]:.2%}
Recall           : {best_row["recall"]:.2%}
F1 Score         : {best_row["f1"]:.2%}
ROC-AUC          : {best_row["roc_auc"]:.2%}
PR-AUC           : {best_row["pr_auc"]:.2%}

Benchmark saved  : {OUTPUT_PATH}

Website model    : {website_model_path}
""")

print("=" * 70)
print("BENCHMARK COMPLETE")
print("=" * 70)