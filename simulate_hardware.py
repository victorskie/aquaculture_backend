import requests
import math
import random
import time

# The exact endpoint extracted from your ESP32 code
API_URL = "https://aquaculture-backend-fz81.onrender.com/api/telemetry/upload/"

def clamp_delta(target, current, max_delta):
    """Ensures the difference between current and target never exceeds max_delta."""
    if current is None:
        return target
    delta = target - current
    if abs(delta) > max_delta:
        # Clamp the change to the maximum allowed limit
        return current + (max_delta if delta > 0 else -max_delta)
    return target

def generate_presentation_data():
    print("Starting rapid data injection to Render Backend (10 total readings)...")
    
    # Track previous state to enforce delta limits
    prev_a = {"temp": None, "ph": None, "turb": None}
    prev_b = {"temp": None, "ph": None, "turb": None}
    
    # Strict Delta Limits (Set just below the failure thresholds)
    LIMIT_TEMP = 1.45  # Must be < 1.5
    LIMIT_PH = 0.45    # Must be < 0.5
    LIMIT_TURB = 14.5  # Must be < 15.0
    
    for i in range(5):
        # 1. Base values (adjusted so a clamped step can still breach absolute limits)
        base_temp = 28 + 2 * math.sin(i * 0.3)
        base_ph = 6.8 + random.uniform(-0.02, 0.02) # Starts closer to the 6.43 failure limit
        base_turb = 8.5 + random.uniform(0.1, 0.5)  # Starts closer to the 22.38 failure limit

        target_a_temp, target_a_ph, target_a_turb = base_temp, base_ph, base_turb
        target_b_temp, target_b_ph, target_b_turb = base_temp + 0.1, base_ph - 0.02, base_turb + 0.2

        # 2. Inject Target Anomalies 
        if i == 1:
            print("[!] TARGETING ANOMALY: Node A - pH absolute limit breach")
            target_a_ph = 5.0 # The clamp will restrict this drop to exactly -0.45
        elif i == 3:
            print("[!] TARGETING ANOMALY: Node B - Turbidity absolute limit breach")
            target_b_turb = 50.0 # The clamp will restrict this spike to exactly +14.5

        # 3. Apply the Delta Limits
        node_a_temp = clamp_delta(target_a_temp, prev_a["temp"], LIMIT_TEMP)
        node_a_ph = clamp_delta(target_a_ph, prev_a["ph"], LIMIT_PH)
        node_a_turb = clamp_delta(target_a_turb, prev_a["turb"], LIMIT_TURB)
        
        node_b_temp = clamp_delta(target_b_temp, prev_b["temp"], LIMIT_TEMP)
        node_b_ph = clamp_delta(target_b_ph, prev_b["ph"], LIMIT_PH)
        node_b_turb = clamp_delta(target_b_turb, prev_b["turb"], LIMIT_TURB)
        
        # 4. Save state for the next loop
        prev_a = {"temp": node_a_temp, "ph": node_a_ph, "turb": node_a_turb}
        prev_b = {"temp": node_b_temp, "ph": node_b_ph, "turb": node_b_turb}

        # Build JSON Payloads
        payloads = [
            {
                "node_name": "Node A",
                "temperature": round(node_a_temp, 2),
                "ph_level": round(node_a_ph, 2),
                "turbidity": round(node_a_turb, 1)
            },
            {
                "node_name": "Node B",
                "temperature": round(node_b_temp, 2), 
                "ph_level": round(node_b_ph, 2),
                "turbidity": round(node_b_turb, 1)
            }
        ]

        # Send the data
        for payload in payloads:
            try:
                response = requests.post(API_URL, json=payload)
                print(f"Sent {payload['node_name']} (Loop {i+1}/5): Status {response.status_code}")
                
                try:
                    ai_reply = response.json()
                    if ai_reply.get("water_change_requested", False):
                        print(f"   >>> AI OVERRIDE TRIGGERED FOR {payload['node_name']} <<<")
                except:
                    pass

            except Exception as e:
                print(f"Failed to send: {e}")
            
            # 1-second pause to prevent simultaneous database timestamp collisions
            time.sleep(1) 
            
        print("\n[SYSTEM] Moving to the next reading cycle...\n")

generate_presentation_data()