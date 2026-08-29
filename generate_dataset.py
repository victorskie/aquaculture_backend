import pandas as pd
import numpy as np
import math
import random

def generate_undetectable_pond_data():
    print("Generating highly realistic raw telemetry (Pre-SMOTE)...")
    
    num_rows = 10500 
    data = []
    
    # Starting realistic baselines
    current_temp = 27.5
    current_ph = 7.3
    current_turb = 5.0
    
    time_until_change = random.randint(384, 480) # 4 to 5 days
    
    for i in range(num_rows):
        # 1. Water Change Reset
        if time_until_change <= 0:
            current_ph = random.gauss(7.2, 0.05)
            current_turb = random.gauss(2.0, 0.5)
            time_until_change = random.randint(384, 480)
        else:
            time_until_change -= 1

        # 2. Diurnal Targets (Where the water "wants" to be based on the sun)
        time_of_day_factor = math.sin((i % 96) * (2 * math.pi / 96))
        target_temp = 28.5 + (time_of_day_factor * 2.5)
        
        # pH multi-day drift target
        ph_drift = math.sin(i * (2 * math.pi / 350)) * 0.5
        target_ph = 7.3 + ph_drift + (time_of_day_factor * 0.15)

        # 3. Brownian Motion (Organic wandering toward the target)
        # The reading moves slightly toward the target, plus Gaussian sensor noise
        current_temp += (target_temp - current_temp) * 0.1 + random.gauss(0, 0.15)
        current_ph += (target_ph - current_ph) * 0.05 + random.gauss(0, 0.03)
        
        # Turbidity slowly climbs as the pond gets dirtier, with feeding spikes
        if i % 96 in [32, 33, 68, 69]: # Feeding time creates a wider, messy spike
            current_turb += random.gauss(6.0, 2.0)
        else:
            current_turb += random.gauss(0.02, 0.3) # Slow dirt accumulation
            
        current_turb = max(0.0, current_turb) # Prevent impossible negative turbidity

        # 4. Inject Danger Events (~8% chance)
        # Using realistic, messy spikes rather than flat limits
        anomaly_chance = random.random()
        if anomaly_chance < 0.08:
            fault_type = random.choice(['temp_high', 'temp_low', 'ph_crash', 'turb_spike', 'sensor_glitch'])
            if fault_type == 'temp_high':
                current_temp += random.gauss(4.0, 1.0)
            elif fault_type == 'temp_low':
                current_temp -= random.gauss(4.0, 1.0)
            elif fault_type == 'ph_crash':
                current_ph -= random.gauss(1.5, 0.4)
            elif fault_type == 'turb_spike':
                current_turb += random.gauss(15.0, 3.0)
            elif fault_type == 'sensor_glitch':
                # Simulates a one-off electrical spike in the ESP32 ADC
                current_ph += random.choice([-1.0, 1.0])

        # 5. Sensor Quantization (Rounding to realistic hardware precision)
        temp_val = round(current_temp, 2)
        ph_val = round(current_ph, 2)
        turb_val = round(current_turb, 1)

        # 6. Calculate Deltas
        if i == 0:
            temp_delta, ph_delta, turb_delta = 0.0, 0.0, 0.0
        else:
            temp_delta = round(temp_val - prev_temp, 2)
            ph_delta = round(ph_val - prev_ph, 2)
            turb_delta = round(turb_val - prev_turb, 1)

        # 7. Labelling Logic (Applying your exact thresholds)
        is_safe = 1 
        
        if not (25.0050 <= temp_val <= 32.0400): is_safe = 0
        if not (6.4300 <= ph_val <= 8.5350): is_safe = 0
        if turb_val > 22.3850: is_safe = 0
            
        if abs(temp_delta) >= 1.5 and time_until_change > 0: is_safe = 0
        if abs(ph_delta) >= 0.5 and time_until_change > 0: is_safe = 0
        if turb_delta >= 15.0 and time_until_change > 0: is_safe = 0

        prev_temp, prev_ph, prev_turb = temp_val, ph_val, turb_val
        
        data.append([temp_val, ph_val, turb_val, temp_delta, ph_delta, turb_delta, is_safe])

    # 8. Export
    columns = ['temperature', 'ph_level', 'turbidity', 'temp_delta', 'ph_delta', 'turb_delta', 'is_safe']
    df = pd.DataFrame(data, columns=columns)
    
    safe_count = len(df[df['is_safe'] == 1])
    unsafe_count = len(df[df['is_safe'] == 0])
    print(f"\nHighly Realistic Dataset Generated!")
    print(f"Total Rows: {len(df)}")
    print(f"Safe Readings (1): {safe_count} ({round((safe_count/len(df))*100, 1)}%)")
    print(f"Unsafe Readings (0): {unsafe_count} ({round((unsafe_count/len(df))*100, 1)}%)")
    
    df.to_csv('aquaculture_dataset_v2.csv', index=False)
    print("\nSaved as 'aquaculture_dataset_v2.csv'")

if __name__ == "__main__":
    generate_undetectable_pond_data()