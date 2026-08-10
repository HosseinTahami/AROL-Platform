from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    VISIBILITY_FULL = "full"
    VISIBILITY_TECHNICIAN = "technician"
    VISIBILITY_COMMERCIAL = "commercial"

    VISIBILITY_CHOICES = [
        (VISIBILITY_FULL, "Full"),
        (VISIBILITY_TECHNICIAN, "Technician"),
        (VISIBILITY_COMMERCIAL, "Commercial"),
    ]

    company = models.ForeignKey(
        "Company",
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True
    )

    job_title = models.CharField(max_length=128, blank=True)

    visibility = models.CharField(
        max_length=32,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_TECHNICIAN
    )

    def __str__(self):
        return self.username


class Company(models.Model):

    company_id = models.CharField(max_length=64, primary_key=True)
    company_name = models.CharField(max_length=128)
    country = models.CharField(max_length=128)
    city = models.CharField(max_length=128)
    sector = models.CharField(max_length=128)
    currency = models.CharField(max_length=8)
    locale = models.CharField(max_length=32)

    class Meta:
        verbose_name_plural = "Companies"


    def __str__(self):
        return self.company_name



class MachineModel(models.Model):

    model_id = models.CharField(max_length=64, primary_key=True)
    model_code = models.CharField(max_length=64)
    description = models.CharField(max_length=256, blank=True)
    primitive_diameter = models.FloatField(null=True, blank=True)
    cap_type = models.CharField(max_length=128, blank=True)
    container_type = models.CharField(max_length=128, blank=True)
    nominal_heads = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    industry_segment = models.CharField(max_length=128, blank=True)

    def __str__(self):
        return f"{self.model_code} | {self.model_id}"

    class Meta:
        verbose_name_plural = "Machine Models"


class Machine(models.Model):

    PLC_SIEMENS = "SIEMENS-SIMATIC-S7"
    PLC_LINE_INTEGRATED = "LINE-PLC-INTEGRATED"
    PLC_HARDWIRED = "HARDWIRED-CONTROL-PANEL"

    PLC_FAMILY_CHOICES = [
        (PLC_SIEMENS, "Siemens Simatic S7"),
        (PLC_LINE_INTEGRATED, "Line PLC Integrated"),
        (PLC_HARDWIRED, "Hardwired Control Panel"),
    ]

    machine_id = models.CharField(max_length=64, primary_key=True)

    company = models.ForeignKey(
        "Company",
        on_delete=models.CASCADE,
        related_name="machines"
    )

    model = models.ForeignKey(
        "MachineModel",
        on_delete=models.PROTECT,
        related_name="machines"
    )

    serial_number = models.CharField(max_length=64, unique=True)
    delivery_date = models.DateField(null=True, blank=True)
    plant_location = models.CharField(max_length=256, blank=True)
    configuration_profile = models.TextField(blank=True)

    plc_family = models.CharField(
        max_length=32, 
        choices=PLC_FAMILY_CHOICES,
        blank=True
    )

    software_version = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return f"{self.serial_num} | {self.machine_id}"