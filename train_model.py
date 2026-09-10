import pandas as pd
import joblib
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parent

csv_path = ROOT / "data" / "processed" / "meghalaya_training_static.csv"
model_path = ROOT / "models" / "random_forest_static.joblib"

df = pd.read_csv(csv_path)

features = [
    "elevation",
    "slope",
    "aspect",
    "curvature",
    "landcover_class",
]

X = df[features].copy()
y = df["label"].astype(int)

model = RandomForestClassifier(
    n_estimators=300,
    random_state=42,
    class_weight="balanced",
    n_jobs=-1,
)

model.fit(X, y)

joblib.dump(model, model_path)

print("\nMODEL SAVED:")
print(model_path)

print("\nFEATURE IMPORTANCE:")
for name, importance in sorted(
    zip(features, model.feature_importances_),
    key=lambda x: x[1],
    reverse=True,
):
    print(f"{name:20s} {importance:.6f}")

print("\nTRAINING ROWS:", len(df))
print("FEATURES:", features)
