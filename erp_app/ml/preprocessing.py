import pandas as pd
import os

BASE_DIR = os.path.dirname(__file__)

# Input dataset path
input_path = os.path.abspath(os.path.join(BASE_DIR, "../data/dataset.csv"))

# Output path
output_path = os.path.abspath(os.path.join(BASE_DIR, "../data/final_dataset.csv"))

print("Reading from:", input_path)
print("Saving to:", output_path)

df = pd.read_csv(input_path)
df = df.fillna("")

all_symptoms = set()

for col in df.columns[1:]:
    all_symptoms.update(df[col].astype(str).str.strip().unique())

all_symptoms.discard("")
new_df = pd.DataFrame()
new_df["prognosis"] = df["Disease"]

for symptom in all_symptoms:
    new_df[symptom] = 0

for i, row in df.iterrows():
    for col in df.columns[1:]:
        symptom = str(row[col]).strip()
        if symptom != "":
            new_df.at[i, symptom] = 1

new_df.to_csv(output_path, index=False)

print("✅ final_dataset.csv CREATED SUCCESSFULLY")