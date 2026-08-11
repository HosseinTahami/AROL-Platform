from rest_framework.generics import ListAPIView

from .models import Machine
from .serializers import MachineSerializer

class MachineListView(ListAPIView):

    serializer_class = MachineSerializer

    def get_queryset(self):
        return Machine.objects.filter(company=self.request.user.company)