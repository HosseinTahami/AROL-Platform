from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from . import views

urlpatterns = [
    path("auth/token/", obtain_auth_token, name="api-token"),
    path("machines/", views.MachineListView.as_view(), name="machine-list"),
    path("machine-models/", views.MachineModelListView.as_view(), name="machinemodel-list"),
    path("alarms/", views.AlarmListView.as_view(), name="alarm-list"),
    path("telemetry/", views.TelemetryListView.as_view(), name="telemetry-list"),
    path("maintenance-tickets/", views.MaintenanceTicketListView.as_view(), name="ticket-list"),
    path("quotes/", views.QuoteListView.as_view(), name="quote-list"),
    path("quote-revisions/", views.QuoteRevisionListView.as_view(), name="quoterevision-list"),
    path("quote-lines/", views.QuoteLineListView.as_view(), name="quoteline-list"),
    path("orders/", views.OrderListView.as_view(), name="order-list"),
    path("order-lines/", views.OrderLineListView.as_view(), name="orderline-list"),
    path("machines/<str:machine_id>/check/", views.MachineCheckView.as_view(), name="machine-check"),
    path("me/", views.MeView.as_view(), name="me"),
]