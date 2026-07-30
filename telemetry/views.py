import json
import os
import joblib
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import SensorReading, SystemConfiguration

# Load the NEW V2 trained ML model
MODEL_PATH = os.path.join(settings.BASE_DIR, 'aquaculture_model_v2.pkl')
try:
    ml_model = joblib.load(MODEL_PATH)
except Exception as e:
    ml_model = None
    print(f"Warning: Could not load the V2 ML model. {e}")

@csrf_exempt
def upload_data(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Default to Node A if your test script hasn't been updated to send a name yet
            node_name = data.get('node_name', 'Node A') 
            temp = float(data['temperature'])
            ph = float(data['ph_level'])
            turb = float(data['turbidity'])
            
            # --- THE PREDICTIVE ENGINE (Calculate Rate of Change) ---
            # 1. Fetch the exact last reading for THIS specific node
            prev_reading = SensorReading.objects.filter(node_name=node_name).order_by('-timestamp').first()
            
            # 2. Calculate the deltas
            if prev_reading:
                temp_delta = round(temp - prev_reading.temperature, 2)
                ph_delta = round(ph - prev_reading.ph_level, 2)
                turb_delta = round(turb - prev_reading.turbidity, 2)
            else:
                # If this is the very first reading in the database, assume 0 change
                temp_delta = 0.0
                ph_delta = 0.0
                turb_delta = 0.0
            
            # 3. Ask the V2 AI for a prediction using all 6 variables!
            is_safe_prediction = None
            if ml_model is not None:
                prediction = ml_model.predict([[temp, ph, turb, temp_delta, ph_delta, turb_delta]])
                is_safe_prediction = bool(prediction[0])
            
            # 4. Save the new reading to the database, including the node name
            SensorReading.objects.create(
                node_name=node_name,
                temperature=temp, 
                ph_level=ph, 
                turbidity=turb, 
                is_safe=is_safe_prediction
            )
            
            # --- POLLING LOGIC FOR RELAY OVERRIDE ---
            config, created = SystemConfiguration.objects.get_or_create(id=1)
            trigger_water_change = config.water_change_requested
            
            if trigger_water_change:
                config.water_change_requested = False
                config.save()
            
            return JsonResponse({
                "status": "success", 
                "message": f"Data for {node_name} saved safely!",
                "ai_evaluation": "Safe" if is_safe_prediction else "Failure Warning!",
                "water_change_requested": trigger_water_change 
            }, status=201)
            
        except (KeyError, ValueError, json.JSONDecodeError):
            return JsonResponse({"status": "error", "message": "Invalid data format"}, status=400)
            
    return JsonResponse({"status": "error", "message": "Only POST requests allowed"}, status=405)


# --- HELPER FUNCTION FOR DASHBOARD LOGIC ---
def has_parameter_failure(node):
    """
    Checks if a node's physical readings are outside safe biological limits.
    Adjust these limits as needed for your specific fish species.
    """
    if not node:
        return False
    # Example safe ranges: Temp (20.0 - 35.0 °C), pH (6.5 - 8.5), Turbidity (< 50.0 %)
    if not (20.0 <= node.temperature <= 35.0): return True
    if not (6.5 <= node.ph_level <= 8.5): return True
    if node.turbidity >= 50.0: return True
    return False

def dashboard(request):
    config, created = SystemConfiguration.objects.get_or_create(id=1)

    # Listen for the manual override button
    if request.method == 'POST' and 'toggle_water_change' in request.POST:
        config.water_change_requested = True
        config.save()
        return redirect('dashboard')

    # Get the absolute latest reading for EACH node independently
    latest_a = SensorReading.objects.filter(node_name="Node A").order_by('-timestamp').first()
    latest_b = SensorReading.objects.filter(node_name="Node B").order_by('-timestamp').first()

    # --- GLOBAL AI DECISION LOGIC ---
    reasons = []
    system_status = "SAFE"

    # Evaluate Node A
    if latest_a and not latest_a.is_safe:
        if has_parameter_failure(latest_a):
            reasons.append("Node A Parameter Failure")
        else:
            reasons.append("Node A Rapid Rate of Change (Delta Warning)")

    # Evaluate Node B
    if latest_b and not latest_b.is_safe:
        if has_parameter_failure(latest_b):
            reasons.append("Node B Parameter Failure")
        else:
            reasons.append("Node B Rapid Rate of Change (Delta Warning)")

    # Determine Overall System Status
    if reasons:
        system_status = "WARNING"
        failure_reasons_str = " | ".join(reasons)
    else:
        failure_reasons_str = ""

    # Fetch the last 20 readings for the graph/table (10 from A, 10 from B)
    recent_readings = SensorReading.objects.all().order_by('-timestamp')[:20]
    
    context = {
        'system_status': system_status,
        'failure_reasons': failure_reasons_str,
        'history': recent_readings,
        'water_change_requested': config.water_change_requested
    }
    
    return render(request, 'telemetry/dashboard.html', context)