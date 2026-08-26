import csv
import random

def generate_dataset():
    # 1. Configuration
    filename = 'aquaculture_dataset_v2.csv'
    num_rows = 10000

    # Ensure these header names exactly match what your train_model.py expects
    headers = ['temperature', 'ph_level', 'turbidity', 'temp_delta', 'ph_delta', 'turb_delta', 'is_safe']

    print(f"Generating {num_rows} rows of predictive aquaculture data...")

    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)

        for _ in range(num_rows):
            # 2. Generate random base values (Simulating current sensor readings)
            # Ranges cover both safe biological limits and dangerous extremes
            temp = round(random.uniform(20.0, 36.0), 2)
            ph = round(random.uniform(5.0, 10.0), 2)
            turb = round(random.uniform(0.0, 50.0), 2)

            # 3. Generate random delta values (Simulating the rate of change)
            # Ranges include normal gradual shifts and violent sudden shocks
            temp_delta = round(random.uniform(-4.0, 4.0), 2)
            ph_delta = round(random.uniform(-1.5, 1.5), 2)
            turb_delta = round(random.uniform(-20.0, 20.0), 2)

            # 4. The Labeling Engine (Determining if the water is Safe (1) or Failure (0))
            is_safe = 1  # Default to safe

            # --- A. Check Absolute Thresholds ---
            if not (24.94 <= temp <= 32.06): 
                is_safe = 0
            if not (6.43 <= ph <= 8.56): 
                is_safe = 0
            if turb > 22.57: 
                is_safe = 0

            # --- B. OVERRIDE: Check for Rapid Rate of Change (Delta Shock) ---
            # Even if the absolute numbers above were safe, these violent shifts force a failure
            if abs(temp_delta) >= 2.0:  
                is_safe = 0
            if abs(ph_delta) >= 0.5:    
                is_safe = 0
            if turb_delta >= 15.0:      
                is_safe = 0

            # 5. Write the fully processed row to the CSV
            writer.writerow([temp, ph, turb, temp_delta, ph_delta, turb_delta, is_safe])

    print(f"Success! Dataset saved to {filename}.")
    print("You can now run 'python train_model.py' to build the new rate-of-change AI logic.")

if __name__ == "__main__":
    generate_dataset()