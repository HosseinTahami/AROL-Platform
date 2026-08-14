import ollama

from core.models import Alarm, TelemetrySnapshot, MaintenanceTicket
from ai.manuals_agent import retrive_chunks

CHAT_MODEL = "qwen3.5:9b"


def gather_operational_data(machine):
    """Pull a machine's recent alarms, latest telemetry, and open tickets."""
    lines = [f"Machine {machine.serial_number} ({machine.machine_id})",
             f"Configuration: {machine.configuration_profile}", ""]

    alarms = Alarm.objects.filter(machine=machine).order_by("-timestamp")[:10]
    lines.append(f"RECENT ALARMS ({alarms.count()} shown):")
    for a in alarms:
        lines.append(f"- {a.alarm_code} | {a.severity} | {a.alarm_status} | {a.timestamp}")

    latest = TelemetrySnapshot.objects.filter(machine=machine).order_by("-timestamp").first()
    if latest:
        lines.append(
            f"\nLATEST TELEMETRY ({latest.timestamp}): status={latest.operational_status}, "
            f"rate={latest.production_rate_bph} bph, uptime={latest.uptime_percentage}%, "
            f"temp={latest.temperature_c}C, alarms this hour={latest.alarm_count}"
        )

    tickets = MaintenanceTicket.objects.filter(machine=machine).exclude(
        ticket_status__in=["Resolved", "Closed"])
    lines.append(f"\nOPEN MAINTENANCE TICKETS ({tickets.count()}):")
    for t in tickets:
        lines.append(f"- {t.ticket_id}: {t.ticket_type} | {t.priority} | {t.ticket_status}")

    return "\n".join(lines)


def diagnose_alarm(machine, alarm_code):
    """Combine structured alarm data with the manual: look up cause/remedy."""
    # Use the alarm code's readable part as the search query into the manual.
    query = alarm_code.replace("_", " ")
    chunks = retrive_chunks(machine, query, top_k=4)
    manual_context = "\n\n".join(
        f"[Page {c.page_num}] {c.content}" for c in chunks
    )

    system_prompt = (
        "You are a troubleshooting assistant for AROL capping machines. "
        "Given an alarm code and manual excerpts, explain the likely cause and "
        "the remedy steps. Use ONLY the manual excerpts. Cite page numbers. "
        "If the manual doesn't cover it, say so."
    )
    user_prompt = (
        f"Machine: {machine.serial_number}\n"
        f"Alarm code: {alarm_code}\n\n"
        f"Manual excerpts:\n{manual_context}\n\n"
        f"Explain the cause and remedy for this alarm."
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


def answer_operational(machine, question):
    """Operational Agent: answer about a machine's alarms/telemetry/maintenance."""
    data = gather_operational_data(machine)

    system_prompt = (
        "You are an operational assistant for AROL capping machines. "
        "Answer using ONLY the machine data provided (alarms, telemetry, tickets). "
        "Be concise and specific. Reference alarm codes and ticket IDs."
    )
    user_prompt = f"{data}\n\nQuestion: {question}"

    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        think=False,
    )
    return {"answer": response["message"]["content"]}