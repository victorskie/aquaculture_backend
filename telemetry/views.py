import json
import os
import joblib
from django.shortcuts import render, redirect # Added redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import SensorReading, SystemConfiguration # Imported the new model

# Load the trained ML model
MODEL_PATH = os.path.join(settings.BASE_DIR, 'aquaculture_model.pkl')
try:
    ml_model = joblib.load(MODEL_PATH)
except Exception as e:
    ml_model = None
    print(f"Warning: Could not load the ML model. {e}")

@csrf_exempt
def upload_data(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            temp = float(data['temperature'])
            ph = float(data['ph_level'])
            turb = float(data['turbidity'])
            
            is_safe_prediction = None
            if ml_model is not None:
                prediction = ml_model.predict([[temp, ph, turb]])
                is_safe_prediction = bool(prediction[0])
            
            # Save the sensor data
            SensorReading.objects.create(
                temperature=temp, ph_level=ph, turbidity=turb, is_safe=is_safe_prediction
            )
            
            # --- NEW POLLING LOGIC ---
            # 1. Grab the current system configuration (create it if it doesn't exist yet)
            config, created = SystemConfiguration.objects.get_or_create(id=1)
            trigger_water_change = config.water_change_requested
            
            # 2. If a water change was requested, reset the switch to False so it only runs once
            if trigger_water_change:
                config.water_change_requested = False
                config.save()
            
            # 3. Send the command back to the ESP32
            return JsonResponse({
                "status": "success", 
                "message": "Data saved safely!",
                "ai_evaluation": "Safe" if is_safe_prediction else "Failure Warning!",
                "water_change_requested": trigger_water_change # The ESP32 looks for this!
            }, status=201)
            
        except (KeyError, ValueError, json.JSONDecodeError):
            return JsonResponse({"status": "error", "message": "Invalid data format"}, status=400)
            
    return JsonResponse({"status": "error", "message": "Only POST requests allowed"}, status=405)


def dashboard(request):
    # Grab the config so we know the current state of the button
    config, created = SystemConfiguration.objects.get_or_create(id=1)

    # If the user clicked the button on the webpage...
    if request.method == 'POST' and 'toggle_water_change' in request.POST:
        config.water_change_requested = True
        config.save()
        return redirect('dashboard') # Refresh the page to show the updated button state

    recent_readings = SensorReading.objects.all().order_by('-timestamp')[:10]
    latest = recent_readings.first() if recent_readings.exists() else None
    
    context = {
        'latest': latest,
        'history': recent_readings,
        'water_change_requested': config.water_change_requested # Pass the state to HTML
    }
    
    return render(request, 'telemetry/dashboard.html', context)