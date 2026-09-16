import json
import os
import joblib
import pandas as pd
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from .models import SensorReading, SystemConfiguration
from . import rules
from django.http import HttpResponse

# Column names and order as used in train_model_v3.py. Predictions are passed as a
# named DataFrame so a mismatch raises instead of silently binding values to the
# wrong features by position.
FEATURE_NAMES = ['temperature', 'ph_level', 'turbidity',
                 'temp_delta', 'ph_delta', 'turb_delta']

# The V3 model is a forecaster: it predicts whether the safety rule will be
# triggered at some point in the next HORIZON_MINUTES. It does not judge the present.
MODEL_PATH = os.path.join(settings.BASE_DIR, 'aquaculture_model_v3.pkl')
try:
    ml_model = joblib.load(MODEL_PATH)
except Exception as e:
    ml_model = None
    print(f"Warning: Could not load the V3 ML model. {e}")

if ml_model is not None and hasattr(ml_model, 'feature_names_in_'):
    trained_names = list(ml_model.feature_names_in_)
    if trained_names != FEATURE_NAMES:
        raise ImproperlyConfigured(
            f"{os.path.basename(MODEL_PATH)} was trained on {trained_names}, "
            f"but this view feeds it {FEATURE_NAMES}. Retrain the model or update "
            f"FEATURE_NAMES so the two agree."
        )

# A delta is only meaningful if the previous reading is one cycle old, give or take.
CYCLE_TOLERANCE_MINUTES = 3
MIN_GAP_MINUTES = rules.CYCLE_MINUTES - CYCLE_TOLERANCE_MINUTES
MAX_GAP_MINUTES = rules.CYCLE_MINUTES + CYCLE_TOLERANCE_MINUTES

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
            
            # 1. Fetch the exact last reading for THIS specific node
            prev_reading = SensorReading.objects.filter(node_name=node_name).order_by('-timestamp').first()

            # 2. A delta is only a rate of change if the previous reading is one
            #    cycle old. A missed cycle makes the difference span an unknown
            #    stretch of time, so it is not comparable to a trained-on delta.
            temp_delta = ph_delta = turb_delta = None
            after_gap = True
            if prev_reading:
                gap_minutes = (timezone.now() - prev_reading.timestamp).total_seconds() / 60.0
                if MIN_GAP_MINUTES <= gap_minutes <= MAX_GAP_MINUTES:
                    temp_delta = round(temp - prev_reading.temperature, 2)
                    ph_delta = round(ph - prev_reading.ph_level, 2)
                    turb_delta = round(turb - prev_reading.turbidity, 2)
                    after_gap = False

            # 3. The verdict for right now comes from the rule, never the model.
            is_safe, failure_type = rules.classify(
                temp, ph, turb, temp_delta, ph_delta, turb_delta
            )

            # 4. The model forecasts the next hour. It needs all six features, so
            #    it sits out a gap; and there is nothing to forecast for water
            #    that has already failed.
            will_fail_60min = None
            if ml_model is not None and not after_gap and is_safe:
                features = pd.DataFrame(
                    [[temp, ph, turb, temp_delta, ph_delta, turb_delta]],
                    columns=FEATURE_NAMES,
                )
                will_fail_60min = bool(ml_model.predict(features)[0])

            # 5. Save the new reading to the database, including the node name
            SensorReading.objects.create(
                node_name=node_name,
                temperature=temp,
                ph_level=ph,
                turbidity=turb,
                temp_delta=temp_delta,
                ph_delta=ph_delta,
                turb_delta=turb_delta,
                after_gap=after_gap,
                is_safe=is_safe,
                failure_type=failure_type,
                will_fail_60min=will_fail_60min,
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
                "ai_evaluation": "Safe" if is_safe else "Failure Warning!",
                "water_change_requested": trigger_water_change,
                "is_safe": is_safe,
                "failure_type": failure_type,
                "after_gap": after_gap,
                "will_fail_60min": will_fail_60min,
            }, status=201)
            
        except (KeyError, ValueError, json.JSONDecodeError):
            return JsonResponse({"status": "error", "message": "Invalid data format"}, status=400)
            
    return JsonResponse({"status": "error", "message": "Only POST requests allowed"}, status=405)


NODE_NAMES = ("Node A", "Node B")

FAILURE_LABELS = {
    'parameter': "Parameter failure",
    'rate': "Rapid rate-of-change failure",
}


def offending_parameters(reading):
    """Name the parameters behind a verdict that was already decided at ingest.

    Presentation only: this explains a stored failure_type, it does not judge
    whether the reading was safe.
    """
    names = []
    if reading.failure_type == 'parameter':
        if not (rules.TEMP_MIN <= reading.temperature <= rules.TEMP_MAX):
            names.append(f"temperature {reading.temperature}°C")
        if not (rules.PH_MIN <= reading.ph_level <= rules.PH_MAX):
            names.append(f"pH {reading.ph_level}")
        if reading.turbidity > rules.TURB_MAX:
            names.append(f"turbidity {reading.turbidity}%")
    elif reading.failure_type == 'rate':
        if reading.temp_delta is not None and abs(reading.temp_delta) > rules.D_TEMP_MAX:
            names.append(f"temperature {reading.temp_delta:+g}°C per cycle")
        if reading.ph_delta is not None and abs(reading.ph_delta) > rules.D_PH_MAX:
            names.append(f"pH {reading.ph_delta:+g} per cycle")
        if reading.turb_delta is not None and abs(reading.turb_delta) > rules.D_TURB_MAX:
            names.append(f"turbidity {reading.turb_delta:+g}% per cycle")
    return names


def dashboard(request):
    # The verdict was decided at ingest and stored on the row; read it, don't redo it.
    failure_reasons = []
    forecast_nodes = []
    for node_name in NODE_NAMES:
        reading = SensorReading.objects.filter(node_name=node_name).order_by('-timestamp').first()
        if reading is None:
            continue
        if reading.is_safe is False:
            label = FAILURE_LABELS.get(reading.failure_type, "Failure")
            detail = ", ".join(offending_parameters(reading)) or "cause not recorded"
            failure_reasons.append(f"{node_name}: {label} ({detail})")
        elif reading.will_fail_60min:
            forecast_nodes.append(node_name)

    if failure_reasons:
        banner_state = 'warning'
    elif forecast_nodes:
        banner_state = 'early'
    else:
        banner_state = 'optimal'

    # Fetch the last 20 readings for the graph/table (10 from A, 10 from B)
    recent_readings = SensorReading.objects.all().order_by('-timestamp')[:20]

    context = {
        'banner_state': banner_state,
        'failure_reasons': failure_reasons,
        'forecast_nodes': " and ".join(forecast_nodes),
        'horizon_minutes': rules.HORIZON_MINUTES,
        'history': recent_readings,
    }

    return render(request, 'telemetry/dashboard.html', context)

def ping(request):
    return HttpResponse("OK")