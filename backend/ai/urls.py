from django.urls import path
from ai.views import ChatView

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat")
]