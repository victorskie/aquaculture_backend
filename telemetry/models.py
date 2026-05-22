from django.db import models

class SensorReading(models.Model):
    temperature = models.FloatField(help_text="Water temperature in °C")
    ph_level = models.FloatField(help_text="Water pH level (0-14)")
    turbidity = models.FloatField(help_text="Water turbidity")
    
    # Automatically records the exact time the ESP32 sends the data
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # We will use this field later when we integrate the Decision Tree model
    is_safe = models.BooleanField(null=True, blank=True, help_text="AI Prediction: True=Safe, False=Failure")

    def __str__(self):
        return f"Reading at {self.timestamp.strftime('%Y-%m-%d %H:%M')} - Temp: {self.temperature}°C"
    

    
class SystemConfiguration(models.Model):
    # This acts as our global switch.
    water_change_requested = models.BooleanField(default=False, help_text="True if the user clicked the manual override button.")

    def __str__(self):
        return f"Water Change Requested: {self.water_change_requested}"