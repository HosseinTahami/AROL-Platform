from django.urls import path
from .views import MachineListView

urlpatterns = [
    path("machines/", MachineListView.as_view(), name="machine-list")
]