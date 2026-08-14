import json
import ollama

from ai.manuals_agent import answer_from_manual
from ai.commercial_agent import answer_commercial
from ai.operational_agent import answer_operational, diagnose_alarm

CHAT_MODEL = "qwen3.5:9b"

VISIBILITY_ALLOWED = {
    "full" : {"manuals", "operational", "commercial"},
    "technician" : {"manuals", "operational"},
    "commercial" : {"manuals", "commercial"}
}


def classify_question(question):

    "Which agent should handle the user's question ??"

    system_prompt = """
        You are a router for an industrial assistant.
        Classify the user's question into exactly one category:
        - 'Manuals': how-to, procedures, specifications, troubleshooting from the manual\n"
        - 'Operational': alarms, telemetry, machine health, maintenance tickets
        - 'Commercial': orders, quotes, prices, deliveries, contracts
        Respond with ONLY and ONLY the category word, nothing else.
    """

    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        think=False,
    )

    raw = response["message"]["content"].strip().lower()

    for category in ("manuals", "operational", "commercial"):
        if category in raw:
            return category

    return "manuals" 


def orchestrate(user, machine, question):

    """
    The 'Main Entry Point' which will routes the user's question
    to the correct agent with enforcing company scope and visibility.
    """

    # 1. Company scope: the machine must belong to the user's company.
    if machine is not None and machine.company_id != user.company_id:
        return {
            "answer": "I can only answer questions about your own company's machines.",
            "agent": None,
            "refused": True,
        }

    # 2. Decide which agent
    question_type = classify_question(question)


    # 3. Visibility enforcement
    allowed = VISIBILITY_ALLOWED.get(user.visibility, set())

    if question_type not in allowed:
        return {
            "answer" : f"Your access level ({user.visibility}) does not permit "
                       f"{question_type} information.",
            "agent" : question_type,
            "refused" : True,
        }

    # 4. Route to the correct agent
    if question_type == "manuals":
        result = answer_from_manual(machine, question)

    elif question_type == "operational":
        result = answer_operational(machine, question)

    elif question_type == "commercial":
        result = answer_commercial(user.company, question)

    else:
        result = {"answer": "I'm not sure how to help with that."}


    result["agent"] = question_type
    result["refused"] = False
    return result