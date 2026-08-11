from rest_framework import serializers

from . import models


class MachineSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Machine
        fields = "__all__"