from rest_framework.views import APIView
from rest_framework.response import Response

from core.models import Machine



from ai.orchestrator.graph import graph as orchestrator_graph


class ChatView(APIView):
    def post(self, request):
        question = request.data.get("question")
        machine_id = request.data.get("machine_id")

        if not question:
            return Response({"error": "A 'question' is required."}, status=400)

        result = orchestrator_graph.invoke({
            "question": question,
            "user_id": request.user.id,
            "machine_id": machine_id or "",
            "refused": False,
            "refusal_reason": "",
            "agents_to_call": [],
            "agent_results": {},
            "final_answer": "",
            "trace": [],
        })

        if result["refused"]:
            return Response({
                "answer": result["refusal_reason"],
                "agents": [],
                "refused": True,
                "trace": result["trace"],
            })

        # merge sources from every agent that ran
        sources = []
        for res in result["agent_results"].values():
            sources.extend(res.get("sources", []))

        return Response({
            "answer": result["final_answer"],
            "agents": result["agents_to_call"],
            "sources": sources,
            "refused": False,
            "trace": result["trace"],
        })

    