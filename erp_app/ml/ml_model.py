import joblib
import pandas as pd
import os

BASE_DIR = os.path.dirname(__file__)

model = joblib.load(os.path.join(BASE_DIR, "ml_model.pkl"))
features = joblib.load(os.path.join(BASE_DIR, "features.pkl"))

def predict_disease(symptoms):

    data = dict.fromkeys(features, 0)

    for s in symptoms:
        if s in data:
            data[s] = 1

    df = pd.DataFrame([data])

    prediction = model.predict(df)[0]

    return prediction