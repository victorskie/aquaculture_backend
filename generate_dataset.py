import csv
import random

# The name of the file we are creating
filename = "aquaculture_dataset.csv"
headers = ["temperature", "ph_level", "turbidity", "is_safe"]

# We will generate 2,000 data points to give the AI enough examples
total_rows = 2000

print(f"Generating {total_rows} rows of synthetic aquaculture data...")

with open(filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(headers)

    for _ in range(total_rows):
        # We want roughly 65% of the data to be "Safe" and 35% to be "Failures"
        # This teaches the AI to recognize both normal days and emergencies.
        if random.random() < 0.65:
            # SAFE CONDITION: All parameters within the normal proposal ranges
            temp = round(random.uniform(25.0, 32.0), 2)
            ph = round(random.uniform(6.5, 8.5), 2)
            turb = round(random.uniform(30.0, 80.0), 2)
            is_safe = 1 # 1 means Safe
        else:
            # FAILURE CONDITION: Start with normal baseline...
            temp = round(random.uniform(25.0, 32.0), 2)
            ph = round(random.uniform(6.5, 8.5), 2)
            turb = round(random.uniform(30.0, 80.0), 2)
            
            # ...then randomly force one or more parameters into the toxic/danger zone
            fail_trigger = random.choice(['temp', 'ph', 'turb', 'combined'])
            
            if fail_trigger == 'temp':
                # Temperature spikes too hot or drops too cold
                temp = round(random.choice([random.uniform(20.0, 24.5), random.uniform(32.5, 38.0)]), 2)
            elif fail_trigger == 'ph':
                # Water becomes too acidic or too alkaline
                ph = round(random.choice([random.uniform(4.0, 6.2), random.uniform(8.8, 10.5)]), 2)
            elif fail_trigger == 'turb':
                # Water gets excessively cloudy
                turb = round(random.uniform(85.0, 150.0), 2)
            else:
                # A combined failure (e.g., hot water AND high acidity)
                temp = round(random.uniform(32.5, 38.0), 2)
                ph = round(random.uniform(4.0, 6.2), 2)

            is_safe = 0 # 0 means Failure/Danger

        writer.writerow([temp, ph, turb, is_safe])

print(f"Success! Dataset saved as {filename}")