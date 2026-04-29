import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

BASE_DIR = os.path.dirname(__file__)

# Correct path
data_path = os.path.join(BASE_DIR, "../data/final_dataset.csv")

df = pd.read_csv(data_path)

X = df.drop("prognosis", axis=1)
y = df["prognosis"]

model = RandomForestClassifier(n_estimators=200)
model.fit(X, y)

# Save model in SAME folder
joblib.dump(model, os.path.join(BASE_DIR, "ml_model.pkl"))
joblib.dump(X.columns.tolist(), os.path.join(BASE_DIR, "features.pkl"))

print("✅ Model trained & saved!")