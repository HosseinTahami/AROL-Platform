from rest_framework import serializers

from . import models


class MachineSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Machine
        fields = [
            "machine_id",
            "serial_number",
            "company",
            "model",
            "delivery_date",
            "plant_location",
            "plc_family",
            "software_version"
        ]