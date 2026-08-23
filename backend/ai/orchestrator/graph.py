from core.models import Alarm, Machine, User
from ai.agents.manuals_agent import answer_from_manual, retrive_chunks
from ai.agents.commercial_agent import answer_commercial
from ai.agents.operational_agent import answer_operational
from langgraph.graph import StateGraph, START, END
from typing import TypedDict
import json
import ollama

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
    if (machine is not None) and (machine.company_id != user.company_id):
        return {
            "refused": True,
            "refusal_reason": "I can only answer questions about your own company's machines.",
            "trace": state["trace"] + ["scope_check: refused (wrong company)"],
        }

    return {
        "refused": False,
        "trace": state["trace"] + ["scope_check: ok"]
    }


def planner(state):
    """
        Ask the LLM which agent or agents (it is possible to need more than one)
        are needed.
    """
    system_prompt = (
        "You are a planner for an industrial assistant with four specialists:\n"
        "- manuals: how-to, procedures, specifications, general troubleshooting steps\n"
        "- diagnosis: explaining the CAUSE and REMEDY of a SPECIFIC alarm the "
        "machine has actually raised. Use this when the question asks to explain "
        "or fix a named or described fault - not just report status.\n"
        "- operational: alarm HISTORY, telemetry, machine health status, "
        "maintenance tickets - reporting WHAT happened, not explaining WHY or HOW "
        "to fix it.\n"
        "- commercial: orders, quotes, prices, deliveries, contracts\n\n"
        "Rules:\n"
        "1. A question may need MORE THAN ONE specialist if it spans domains.\n"
        "2. If a recent conversation is shown above the question and the current "
        "question is a follow-up, route based on which specialist's DATA the "
        "earlier statement came from, not the surface wording of the follow-up.\n\n"
        "Worked examples:\n"
        'Q: "What does the low air pressure alarm mean, and what maintenance has '
        'been done recently?"\n'
        'A: ["diagnosis", "operational"]  (explaining a fault = diagnosis; '
        "maintenance history = operational; NOT manuals, because the alarm is "
        "specific and actually occurred)\n\n"
        'Q: "We\'re about to place an order - is the machine running ok?"\n'
        'A: ["commercial", "operational"]  (placing an order = commercial; '
        "current running status = operational)\n\n"
        'Q: "Is there an open order for this machine, and why does it keep '
        'alarming?"\n'
        'A: ["commercial", "diagnosis"]  (order = commercial; explaining a '
        "recurring fault = diagnosis, not operational, because \"why\" asks for "
        "cause)\n\n"
        "Respond with ONLY a JSON list of the needed specialists, e.g. "
        '["diagnosis"] or ["diagnosis", "commercial"]. Nothing else - no '
        "explanation, no markdown formatting."
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

    return {
        "refused": False,
        "trace": state["trace"] + ["visibility_check: ok"]
    }


def run_agents(state):
    """
        Call every agent the planner selected and collect their results.
    """
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
    """
        Resolve which alarm the question is about,
        then diagnose it via the manual.
    """
    recent_alarms = Alarm.objects.filter(
        machine=machine).order_by("-timestamp")[:10]
    matched_code = None
    for a in recent_alarms:
        keywords = [w for w in a.alarm_code.replace("_", " ").lower().split() if len(w) > 3]
        if a.alarm_code.lower() in question.lower() or any(w in question.lower() for w in keywords):
            matched_code = a.alarm_code
            break
    if matched_code is None:
        return answer_operational(machine, question)
    return diagnose_alarm(machine, matched_code)


def diagnose_alarm(machine, alarm_code):
    """
        Combine the alarm's real record with manual excerpts to answer
        either a status question or a cause/remedy question.
    """
    query = alarm_code.replace("_", " ")
    chunks = retrive_chunks(machine, query, top_k=4)
    manual_context = "\n\n".join(
        f"[Page {c.page_num}] {c.content}" for c in chunks
    )

    alarm_record = Alarm.objects.filter(
        machine=machine, alarm_code=alarm_code
    ).order_by("-timestamp").first()

    alarm_facts = ""
    if alarm_record:
        alarm_facts = (
            f"Alarm record: ID {alarm_record.alarm_id}, code {alarm_record.alarm_code}, "
            f"severity {alarm_record.severity}, status {alarm_record.alarm_status}, "
            f"occurred {alarm_record.timestamp}.\n\n"
        )

    system_prompt = (
        "You are a troubleshooting assistant for AROL capping machines. "
        "Given an alarm's record and manual excerpts, answer the question. "
        "If asked for severity/status/timing, use the alarm record fields exactly. "
        "If asked for cause/remedy, use ONLY the manual excerpts and cite page numbers."
    )
    user_prompt = (
        f"Machine: {machine.serial_number}\n"
        f"{alarm_facts}"
        f"Manual excerpts:\n{manual_context}\n\n"
        f"Question about alarm {alarm_code}: answer using the record and excerpts above."
    )

    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        think=False,
    )
    return {
        "answer": response["message"]["content"],
        "sources": [{"page": c.page_num, "file": c.source_file} for c in chunks],
    }


def synthesizer(state):
    """
        Combine one or more agent answers into a single coherent response.
    """
    results = state["agent_results"]
    agent_names = list(results.keys())
    number_of_agents = len(agent_names)
    if number_of_agents == 1:
        only_agent_name = agent_names[0]
        only_result = results[only_agent_name]
        return {
            "final_answer": only_result["answer"],
            "trace": state["trace"] + ["synthesizer: passthrough (single agent)"],
        }
    sections_list = []
    for name, res in results.items():
        header = f"--- {name.upper()} AGENT ---"
        body = res["answer"]
        sections_list.append(f"{header}\n{body}")
    sections = "\n\n".join(sections_list)
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
builder.add_node("scope_check", scope_check)
builder.add_node("planner", planner)
builder.add_node("visibility_check", visibility_check)
builder.add_node("run_agents", run_agents)
builder.add_node("synthesizer", synthesizer)

builder.add_edge(START, "scope_check")
builder.add_conditional_edges("scope_check", route_after_scope, {"planner": "planner", END: END})
builder.add_edge("planner", "visibility_check")
builder.add_conditional_edges("visibility_check", route_after_visibility, {"run_agents": "run_agents", END: END})
builder.add_edge("run_agents", "synthesizer")
builder.add_edge("synthesizer", END)

graph = builder.compile()