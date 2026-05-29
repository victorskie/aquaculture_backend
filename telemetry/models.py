from django.db import models

class SensorReading(models.Model):
    # NEW: Tracks whether this is Node A or Node B
    node_name = models.CharField(max_length=20, default="Node A") 
    
    temperature = models.FloatField()
    ph_level = models.FloatField()
    turbidity = models.FloatField()
    is_safe = models.BooleanField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.node_name} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


    

    
class SystemConfiguration(models.Model):
    # This acts as our global switch.
    water_change_requested = models.BooleanField(default=False, help_text="True if the user clicked the manual override button.")

    def __str__(self):
        return f"Water Change Requested: {self.water_change_requested}"