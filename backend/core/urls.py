from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from .views import MachineListView

urlpatterns = [
    path("machines/", MachineListView.as_view(), name="machine-list"),
    path("auth/token/", obtain_auth_token, name="api_token"),
]