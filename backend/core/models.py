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