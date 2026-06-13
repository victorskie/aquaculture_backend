import csv
import random
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
import joblib

filename = "aquaculture_dataset_v2.csv"
headers = ["temperature", "ph_level", "turbidity", "temp_delta", "ph_delta", "turb_delta", "is_safe"]

print("1. Generating dataset with Independent Failure Modes...")
with open(filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(headers)

    # Increased dataset size for better accuracy
    for _ in range(3000):
        # -----------------------------------------
        # SAFE CONDITION
        # -----------------------------------------
        if random.random() < 0.50:
            temp = round(random.uniform(25.0, 32.0), 2)
            ph = round(random.uniform(6.5, 8.5), 2)
            turb = round(random.uniform(0.0, 20.0), 2) 
            
            t_delta = round(random.uniform(-0.3, 0.3), 2)
            p_delta = round(random.uniform(-0.1, 0.1), 2)
            tu_delta = round(random.uniform(-1.0, 1.0), 2)
            is_safe = 1
            
        # -----------------------------------------
        # FAILURE CONDITION
        # -----------------------------------------
        else:
            # Start with a safe baseline
            temp = round(random.uniform(25.0, 32.0), 2)
            ph = round(random.uniform(6.5, 8.5), 2)
            turb = round(random.uniform(0.0, 20.0), 2)
            
            t_delta = round(random.uniform(-0.3, 0.3), 2)
            p_delta = round(random.uniform(-0.1, 0.1), 2)
            tu_delta = round(random.uniform(-1.0, 1.0), 2)

            # Randomly decide WHICH parameter(s) will fail 
            # (1 = Temp fails, 2 = pH fails, 3 = Turbidity fails, 4 = All fail)
            fail_trigger = random.randint(1, 4)
            
            if fail_trigger in [1, 4]: 
                # Temp drops below 25 or spikes above 32
                temp = round(random.choice([random.uniform(0.0, 24.9), random.uniform(32.1, 50.0)]), 2)
                
            if fail_trigger in [2, 4]: 
                # pH drops below 6.5 or spikes above 8.5 (Covers 0 to 14)
                ph = round(random.choice([random.uniform(0.0, 6.4), random.uniform(8.6, 14.0)]), 2)
                
            if fail_trigger in [3, 4]: 
                # Turbidity goes above 25%
                turb = round(random.uniform(25.0, 100.0), 2)
                
            is_safe = 0

        writer.writerow([temp, ph, turb, t_delta, p_delta, tu_delta, is_safe])

print("2. Training Decision Tree on Independent parameters...")
df = pd.read_csv(filename)
X = df[['temperature', 'ph_level', 'turbidity', 'temp_delta', 'ph_delta', 'turb_delta']]
y = df['is_safe']

model = DecisionTreeClassifier(random_state=42)
model.fit(X, y)

joblib.dump(model, 'aquaculture_model_v2.pkl') 
print("Success! Brain retrained and saved as 'aquaculture_model_v2.pkl'")