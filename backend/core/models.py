from django.db import models

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