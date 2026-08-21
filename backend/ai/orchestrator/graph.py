from core.models import Alarm
import json
import ollama
from langgraph.graph import StateGraph, START, END
from core.models import User, Machine
from ai.agents.manuals_agent import answer_from_manual
from ai.agents.commercial_agent import answer_commercial
from ai.agents.operational_agent import answer_operational
from ai.agents.operational_agent import diagnose_alarm
from typing import TypedDict


CHAT_MODEL = "qwen3.5:9b"

"""
    Every time a  question comes in:
        1. Check: Is this person even allowed to ask about this machine. (Cheking Company)
        2. Decide: Which expert or experts should answer this question? 
        3. Other Check: Is this person allowed to hear from that expert ? (Role Checking)
        4. Answer: Expert answers the question and if there is more than one, then
                   combine their answers into one.
"""

VISIBILITY_ALLOWED = {
    "full": {"manuals", "operational", "commercial", "diagnosis"},
    "technician": {"manuals", "operational", "diagnosis"},
    "commercial": {"manuals", "commercial"},
}



class OrchestratorState(TypedDict):
    question: str
    history: list
    user_id: int
    machine_id: str
    refused: bool
    refusal_reason: str
    agents_to_call: list
    agent_results: dict
    final_answer: str
    trace: list


def format_history(history):

    """
        Turn the recent conversation into
        a short text block for prompts.
    """

    if not history:
        return ""
    lines = ["Recent conversation:"]
    for h in history:
        speaker = "User" if h["role"] == "user" else "Assistant"
        lines.append(f"{speaker}: {h['text']}")
    return "\n".join(lines) + "\n\n"



def scope_check(state):
    user = User.objects.get(id=state["user_id"])
    machine = Machine.objects.filter(machine_id=state["machine_id"]).first()

    if machine is not None and machine.company_id != user.company_id:
        return {
            "refused": True,
            "refusal_reason": "I can only answer questions about your own company's machines.",
            "trace": state["trace"] + ["scope_check: refused (wrong company)"],
        }
    return {"refused": False, "trace": state["trace"] + ["scope_check: ok"]}


def planner(state):
    """Ask the LLM which agent(s) - possibly more than one - are needed."""
    system_prompt = (
        "You are a planner for an industrial assistant with four specialists:\n"
        "- manuals: how-to, procedures, specifications, general troubleshooting steps\n"
        "- diagnosis: explaining the CAUSE and REMEDY of a SPECIFIC alarm the "
        "machine has actually raised (e.g. 'why does it keep alarming for low "
        "air pressure, how do I fix it'). Use this instead of 'operational' when "
        "the question is asking to explain/fix a named or described fault, not "
        "just report status.\n"
        "- operational: alarm HISTORY, telemetry, machine health status, "
        "maintenance tickets - reporting WHAT happened, not explaining WHY or HOW "
        "to fix it.\n"
        "- commercial: orders, quotes, prices, deliveries, contracts\n"
        "A question may need MORE THAN ONE specialist if it spans domains "
        "(e.g. a diagnosis AND whether it's covered by warranty).\n"
        "Respond with ONLY a JSON list of the needed specialists, e.g. "
        '["diagnosis"] or ["diagnosis", "commercial"]. Nothing else.'
        "A question may need MORE THAN ONE specialist if it spans domains "
        "(e.g. a diagnosis AND whether it's covered by warranty).\n"
        "If a recent conversation is included above the question, and the question "
        "is a follow-up (e.g. 'what does that mean', 'why', 'what about X') that "
        "refers to something the assistant said earlier, route based on which "
        "specialist's DATA that earlier statement came from - not the surface "
        "wording of the follow-up alone. For example, if the assistant previously "
        "reported a live production rate or status (operational data) and the user "
        "asks what it means, route to 'operational', not 'manuals', since the value "
        "itself is not defined in the manual.\n"
    )
    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": format_history(state.get("history", [])) + state["question"]},
        ],
        think=False,
    )
    raw = response["message"]["content"].strip()


    try:
        agents = json.loads(raw)
        agents = [a for a in agents if a in ("manuals", "operational", "commercial", "diagnosis")]
    except (json.JSONDecodeError, TypeError):
        agents = ["manuals"]
    if not agents:
        agents = ["manuals"]
    return {"agents_to_call": agents, "trace": state["trace"] + [f"planner: chose {agents}"]}


def visibility_check(state):
    user = User.objects.get(id=state["user_id"])
    allowed = VISIBILITY_ALLOWED.get(user.visibility, set())
    blocked = [a for a in state["agents_to_call"] if a not in allowed]
    if blocked:
        return {
            "refused": True,
            "refusal_reason": f"Your access level ({user.visibility}) does not permit "
                               f"{', '.join(blocked)} information.",
            "trace": state["trace"] + [f"visibility_check: refused ({blocked})"],
        }
    return {"refused": False, "trace": state["trace"] + ["visibility_check: ok"]}


def run_agents(state):
    user = User.objects.get(id=state["user_id"])
    machine = Machine.objects.filter(machine_id=state["machine_id"]).first()
    results = {}
    history_text = format_history(state.get("history", []))
    question_with_context = history_text + state["question"]

    for agent in state["agents_to_call"]:
        if agent == "manuals":
            results["manuals"] = answer_from_manual(machine, question_with_context)
        elif agent == "operational":
            results["operational"] = answer_operational(machine, question_with_context)
        elif agent == "commercial":
            results["commercial"] = answer_commercial(user.company, question_with_context)
        elif agent == "diagnosis":
            results["diagnosis"] = run_diagnosis(machine, question_with_context)
    return {
        "agent_results": results,
        "trace": state["trace"] + [f"agents ran: {list(results.keys())}"],
    }


def run_diagnosis(machine, question):
    """Resolve which alarm the question is about, then diagnose it via the manual."""
    recent_alarms = Alarm.objects.filter(machine=machine).order_by("-timestamp")[:10]
    matched_code = None
    for a in recent_alarms:
        keywords = [w for w in a.alarm_code.replace("_", " ").lower().split() if len(w) > 3]
        if a.alarm_code.lower() in question.lower() or any(w in question.lower() for w in keywords):
            matched_code = a.alarm_code
            break

    if matched_code is None:
        return answer_operational(machine, question)

    return diagnose_alarm(machine, matched_code)


def synthesizer(state):
    """Combine one or more agent answers into a single coherent response."""
    results = state["agent_results"]
    if len(results) == 1:
        only = next(iter(results.values()))
        return {
            "final_answer": only["answer"],
            "trace": state["trace"] + ["synthesizer: passthrough (single agent)"],
        }
    sections = "\n\n".join(
        f"--- {name.upper()} AGENT ---\n{res['answer']}"
        for name, res in results.items()
    )
    system_prompt = (
        "You are combining answers from multiple specialist assistants into ONE "
        "coherent response for the user. Merge the information naturally, avoid "
        "repeating the specialist names, and keep all specific facts and citations."
    )
    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": sections},
        ],
        think=False,
    )
    return {
        "final_answer": response["message"]["content"],
        "trace": state["trace"] + ["synthesizer: combined multiple agents"],
    }


def route_after_scope(state):
    return "planner" if not state["refused"] else END


def route_after_visibility(state):
    return "run_agents" if not state["refused"] else END



builder = StateGraph(OrchestratorState)      

# Register Step:
#   Company-check logic
builder.add_node("scope_check", scope_check)

# Register Step:
#   Routing-Decision Step
builder.add_node("planner", planner)

# Register Step:
#   Role Permission
builder.add_node("visibility_check", visibility_check)

# Register Step:
#   Calls the real agents
builder.add_node("run_agents", run_agents)

# Register Step:
#   Final Merge Step
builder.add_node("synthesizer", synthesizer)

# Connecting the Nodes 
builder.add_edge(START, "scope_check")
builder.add_conditional_edges("scope_check", route_after_scope, {"planner": "planner", END: END})
builder.add_edge("planner", "visibility_check")
builder.add_conditional_edges("visibility_check", route_after_visibility, {"run_agents": "run_agents", END: END})
builder.add_edge("run_agents", "synthesizer")
builder.add_edge("synthesizer", END)

graph = builder.compile()