from rest_framework.generics import ListAPIView


from . import models, serializers
from .permissions import CanSeeCommercial, CanSeeOperational


class MachineListView(ListAPIView):
    serializer_class = serializers.MachineSerializer

    def get_queryset(self):
        return models.Machine.objects.filter(
            company=self.request.user.company
        )


class MachineModelListView(ListAPIView):
    serializer_class = serializers.MachineModelSerializer

    def get_queryset(self):
        # Only models used by this company's machines
        company = self.request.user.company
        return models.MachineModel.objects.filter(
            machines__company=company
        ).distinct()

class AlarmListView(ListAPIView):
    serializer_class = serializers.AlarmSerializer
    permission_classes = [CanSeeOperational]

    def get_queryset(self):
        return models.Alarm.objects.filter(
            machine__company=self.request.user.company
        )

class TelemetryListView(ListAPIView):
    serializer_class = serializers.TelemetrySnapshotSerializer
    permission_classes = [CanSeeOperational]

    def get_queryset(self):
        return models.TelemetrySnapshot.objects.filter(
            machine__company=self.request.user.company
        )

class MaintenanceTicketListView(ListAPIView):
    serializer_class = serializers.MaintenanceTicketSerializer
    permission_classes = [CanSeeOperational]

    def get_queryset(self):
        return models.MaintenanceTicket.objects.filter(
            machine__company=self.request.user.company
        )

class QuoteListView(ListAPIView):
    serializer_class = serializers.QuoteSerializer
    permission_classes = [CanSeeCommercial]

    def get_queryset(self):
        return models.Quote.objects.filter(
            company=self.request.user.company
    )

class QuoteRevisionListView(ListAPIView):
    serializer_class = serializers.QuoteRevisionSerializer
    permission_classes = [CanSeeCommercial]

    def get_queryset(self):
        return models.QuoteRevision.objects.filter(
            quote__company=self.request.user.company
        )

class QuoteLineListView(ListAPIView):
    serializer_class = serializers.QuoteLineSerializer
    permission_classes = [CanSeeCommercial]

    def get_queryset(self):
        return models.QuoteLine.objects.filter(
            quote_revision__quote__company=self.request.user.company
        )

class OrderListView(ListAPIView):
    serializer_class = serializers.OrderSerializer
    permission_classes = [CanSeeCommercial]

    def get_queryset(self):
        return models.Order.objects.filter(
            company=self.request.user.company
        )

class OrderLineListView(ListAPIView):
    serializer_class = serializers.OrderLineSerializer
    permission_classes = [CanSeeCommercial]

    def get_queryset(self):
        return models.OrderLine.objects.filter(
            order__company=self.request.user.company
        )