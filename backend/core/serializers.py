from rest_framework import serializers

from . import models


class MachineSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Machine
        fields = "__all__"


class CompanySerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Company
        fields = "__all__"


class MachineModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.MachineModel
        fields = "__all__"

class AlarmSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Alarm
        fields = "__all__"

class TelemetrySnapshotSerializer(serializers.ModelSerializer):

    class Meta:
        models = models.TelemetrySnapshot
        fields = "__all__"

class MaintenanceTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MaintenanceTicket
        fields = "__all__"


class QuoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Quote
        fields = "__all__"


class QuoteRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.QuoteRevision
        fields = "__all__"


class QuoteLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.QuoteLine
        fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Order
        fields = "__all__"


class OrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OrderLine
        fields = "__all__"