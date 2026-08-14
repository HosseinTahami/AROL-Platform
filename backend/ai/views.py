from rest_framework.views import APIView, Response
from rest_framework.views import Response
from rest_framework import status

from core.models import Machine
from ai.orchestrator import orchestrate


class ChatView(APIView):

    def post(self, request):
        question = request.data.get("question")
        machine_id = request.data.get("machine_id")

        if not question:
            return Response(
                {"error" : "A 'question' is required"},
                status = status.HTTP_400_BAD_REQUEST,
            )

        machine = None

        if machine_id:

            machine = Machine.objects.filter(machine_id=machine_id).first()
            if machine is None:
                return Response(
                    {"error" : f"Machine {machine_id} not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        result = orchestrate(request.user, machine, question)
        return Response(result)