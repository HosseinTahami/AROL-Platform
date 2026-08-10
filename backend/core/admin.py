from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from . import models

admin.site.register(models.Company)
admin.site.register(models.User, UserAdmin)
admin.site.register(models.MachineModel)
admin.site.register(models.Machine)
admin.site.register(models.Alarm)
admin.site.register(models.MaintenanceTicket)
admin.site.register(models.TelemetrySnapshot)