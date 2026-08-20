from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response

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

        """
            MachineModel has a reverse relationship to Machine
            so machines__company means 
            '''
                look at this MachineModel's related Machines,
                and check their company field.
            '''
        """
        return models.MachineModel.objects.filter(
            machines__company=company
        ).distinct()

class AlarmListView(ListAPIView):
    serializer_class = serializers.AlarmSerializer
    permission_classes = [CanSeeOperational]

    def get_queryset(self):

        """
            Alarm doesn't have its own company field,
            but it has a machine, and that has a company.
            
            So machine__company= walks through the relationship
            to filter by the machine's owner.
        """
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

class MachineCheckView(APIView):
    def get(self, request, machine_id):
        machine = models.Machine.objects.filter(machine_id=machine_id).first()
        if machine is None:
            return Response({"valid": False, "reason": "not_found"})
        if machine.company_id != request.user.company_id:
            return Response({"valid": False, "reason": "not_yours"})
        return Response({
            "valid": True,
            "machine_id": machine.machine_id,
            "serial_number": machine.serial_number,
        })

class MeView(APIView):
    def get(self, request):
        u = request.user
        return Response({
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
            "visibility": u.visibility,
            "company": u.company.company_name if u.company else None,
        })