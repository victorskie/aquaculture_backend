import csv
import random
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
import joblib

filename = "aquaculture_dataset_v2.csv"
headers = ["temperature", "ph_level", "turbidity", "temp_delta", "ph_delta", "turb_delta", "is_safe"]

print("1. Generating new dataset with Rate-of-Change physics...")
with open(filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(headers)

    for _ in range(2500):
        if random.random() < 0.60:
            # SAFE: Normal values AND stable changes
            temp = round(random.uniform(25.0, 32.0), 2)
            ph = round(random.uniform(6.5, 8.5), 2)
            turb = round(random.uniform(30.0, 80.0), 2)
            # Very small shifts between readings
            t_delta = round(random.uniform(-0.3, 0.3), 2)
            p_delta = round(random.uniform(-0.1, 0.1), 2)
            tu_delta = round(random.uniform(-2.0, 2.0), 2)
            is_safe = 1
        else:
            # FAILURE: Bad ranges OR dangerous spikes
            fail_type = random.choice(['bad_range', 'rapid_spike'])
            
            if fail_type == 'bad_range':
                # Similar to V1: Bad absolute numbers, but small changes
                temp = round(random.choice([random.uniform(20.0, 24.5), random.uniform(32.5, 38.0)]), 2)
                ph = round(random.choice([random.uniform(4.0, 6.2), random.uniform(8.8, 10.5)]), 2)
                turb = round(random.uniform(85.0, 150.0), 2)
                t_delta = round(random.uniform(-0.3, 0.3), 2)
                p_delta = round(random.uniform(-0.1, 0.1), 2)
                tu_delta = round(random.uniform(-2.0, 2.0), 2)
            else:
                # THE PREDICTIVE UPGRADE: Numbers look safe right now, but are moving too fast!
                temp = round(random.uniform(25.0, 32.0), 2)
                ph = round(random.uniform(6.5, 8.5), 2)
                turb = round(random.uniform(30.0, 80.0), 2)
                # Massive, unnatural shifts between the last 10-minute reading
                t_delta = round(random.choice([random.uniform(1.5, 3.0), random.uniform(-3.0, -1.5)]), 2) # e.g. Heater broke
                p_delta = round(random.choice([random.uniform(0.5, 1.0), random.uniform(-1.0, -0.5)]), 2) # e.g. Chemical spill
                tu_delta = round(random.uniform(15.0, 40.0), 2) # e.g. Mudslide / rapid contamination
                
            is_safe = 0

        writer.writerow([temp, ph, turb, t_delta, p_delta, tu_delta, is_safe])

print("2. Training V2 Decision Tree on new physics...")
df = pd.read_csv(filename)
X = df[['temperature', 'ph_level', 'turbidity', 'temp_delta', 'ph_delta', 'turb_delta']]
y = df['is_safe']

model = DecisionTreeClassifier(random_state=42)
model.fit(X, y)

joblib.dump(model, 'aquaculture_model_v2.pkl')
print("Success! Brain V2 saved as 'aquaculture_model_v2.pkl'")