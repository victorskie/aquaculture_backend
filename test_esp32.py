import requests
import random

# The local URL of your Django API endpoint
url = 'http://127.0.0.1:8000/api/telemetry/upload/'

# Generating some realistic fake data for the fish pond
payload = {
    "node_name": "Node B",
    "temperature": round(random.uniform(26.0, 31.0), 2),
    "ph_level": round(random.uniform(6.5, 8.0), 2),
    "turbidity": round(random.uniform(30.0, 60.0), 2)
}

print(f"Sending data: {payload}")

# Firing the HTTP POST request (exactly what the ESP32 will do)
response = requests.post(url, json=payload)

print(f"Server Response: {response.status_code}")
print(response.json())