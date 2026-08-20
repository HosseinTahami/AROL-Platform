from rest_framework.views import APIView
from rest_framework.response import Response

from core.models import Machine
from core.models import Conversation, Message


from ai.orchestrator.graph import graph as orchestrator_graph


class ChatView(APIView):
    def post(self, request):
        question = request.data.get("question")
        machine_id = request.data.get("machine_id")
        conversation_id = request.data.get("conversation_id")

        if not question:
            return Response({"error": "A 'question' is required."}, status=400)

        machine = Machine.objects.filter(machine_id=machine_id).first() if machine_id else None

        # Find the user's existing conversation, or start a new one.
        if conversation_id:
            conversation = Conversation.objects.filter(
                id=conversation_id, user=request.user
            ).first()
            if conversation is None:
                return Response({"error": "Conversation not found."}, status=404)
        else:
            conversation = Conversation.objects.create(user=request.user, machine=machine)

        # Save the incoming question.
        Message.objects.create(conversation=conversation, role="user", text=question)

        # Load recent history (excluding the message we just saved) for context.
        recent = list(conversation.messages.order_by("-created_at")[1:7])
        recent.reverse()
        history = [{"role": m.role, "text": m.text} for m in recent]

        result = orchestrator_graph.invoke({
            "question": question,
            "history": history,
            "user_id": request.user.id,
            "machine_id": machine_id or "",
            "refused": False,
            "refusal_reason": "",
            "agents_to_call": [],
            "agent_results": {},
            "final_answer": "",
            "trace": [],
        })

        answer_text = result["refusal_reason"] if result["refused"] else result["final_answer"]
        Message.objects.create(conversation=conversation, role="assistant", text=answer_text)

        sources = []
        for res in result.get("agent_results", {}).values():
            sources.extend(res.get("sources", []))

        return Response({
            "conversation_id": conversation.id,
            "answer": answer_text,
            "agents": result["agents_to_call"],
            "sources": sources,
            "refused": result["refused"],
            "trace": result["trace"],
        })
    