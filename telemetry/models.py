from django.db import models

class SensorReading(models.Model):
    # NEW: Tracks whether this is Node A or Node B
    node_name = models.CharField(max_length=20, default="Node A") 
    
    temperature = models.FloatField()
    ph_level = models.FloatField()
    turbidity = models.FloatField()

    temp_delta = models.FloatField(null=True, blank=True)
    ph_delta = models.FloatField(null=True, blank=True)
    turb_delta = models.FloatField(null=True, blank=True)
    after_gap = models.BooleanField(default=False)

    is_safe = models.BooleanField(
        null=True,
        blank=True,
        help_text="Verdict of the safety rule at the moment of the reading, not a model prediction.",
    )
    failure_type = models.CharField(max_length=16, null=True, blank=True)
    will_fail_60min = models.BooleanField(null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    @property
    def transparency_cm(self):
        """Secchi transparency equivalent of the stored turbidity percentage.

        Display only. The turbidity field remains the stored quantity and is
        what the safety rule is applied to; this converts it for presentation
        using D = 0.40 x (100 - T), the relation fixed by the 40 cm Secchi
        tube used during calibration.
        """
        return round(0.40 * (100 - self.turbidity), 1)

    def __str__(self):
        return f"{self.node_name} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


    

    
class SystemConfiguration(models.Model):
    # This acts as our global switch.
    water_change_requested = models.BooleanField(default=False, help_text="True if the user clicked the manual override button.")

    def __str__(self):
        return f"Water Change Requested: {self.water_change_requested}"