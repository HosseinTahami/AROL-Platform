import ollama

from core.models import Alarm, TelemetrySnapshot, MaintenanceTicket
from ai.agents.manuals_agent import retrive_chunks

CHAT_MODEL = "qwen3.5:9b"


def gather_operational_data(machine):

    """
        Gathers recent 

            - alarms
            - latest telemetry
            - open tickets 

        of a machine.
    
    """



    gathered_data = [f"Machine {machine.serial_number} ({machine.machine_id})",
             f"Configuration: {machine.configuration_profile}", ""]

    alarms = Alarm.objects.filter(machine=machine).order_by("-timestamp")[:10]

    gathered_data.append(f"RECENT ALARMS ({alarms.count()} shown):")

    for alarm in alarms:
        gathered_data.append(f"- ID: {alarm.alarm_id} | Code: {alarm.alarm_code} | Severity: {alarm.severity} | Status: {alarm.alarm_status} | Time: {alarm.timestamp}")

    latest = TelemetrySnapshot.objects.filter(machine=machine).order_by("-timestamp").first()

    if latest:
        gathered_data.append(
            f"\nLATEST TELEMETRY ({latest.timestamp}): status={latest.operational_status}, "
            f"rate={latest.production_rate_bph} bph, uptime={latest.uptime_percentage}%, "
            f"temp={latest.temperature_c}C, alarms this hour={latest.alarm_count}"
        )

    # Only the Maintenance Tickets with OPEN status
    tickets = MaintenanceTicket.objects.filter(machine=machine).exclude(
        ticket_status__in=["Resolved", "Closed"])
    gathered_data.append(f"\nOPEN MAINTENANCE TICKETS ({tickets.count()}):")


    for ticket in tickets:
        gathered_data.append(f"- {ticket.ticket_id}: {ticket.ticket_type} | {ticket.priority} | {ticket.ticket_status}")

    return "\n".join(gathered_data)


def diagnose_alarm(machine, alarm_code):

    """
        Combine structured alarm data with the manual.
    """

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

    """
        Operational Agent:
          
          answer about a machine's alarms, telemetry and maintenance,
          automatically consulting the manual if the question concerns
          a specific alarm.
    
    """
    data = gather_operational_data(machine)

    # Check if the question is asking about one of this machine's actual alarm codes.
    # If so, pull the manual's explanation for it too.
    diagnosis_context = ""

    recent_alarms = Alarm.objects.filter(machine=machine).order_by("-timestamp")[:10]

    mentioned_code = None

    for a in recent_alarms:

        # crude but effective: does the question reference this alarm's code
        # or its readable keywords (e.g. "air pressure" for AL017_LOW_AIR_PRESSURE)?
        readable = a.alarm_code.replace("_", " ").lower()
        keywords = [w for w in readable.split() if len(w) > 3]

        if a.alarm_code.lower() in question.lower() or any(w in question.lower() for w in keywords):
            mentioned_code = a.alarm_code
            break

    if mentioned_code:
        diagnosis = diagnose_alarm(machine, mentioned_code)
        diagnosis_context = (
            f"\n\nMANUAL GUIDANCE for {mentioned_code} "
            f"(sources: {[s['page'] for s in diagnosis['sources']]}):\n"
            f"{diagnosis['answer']}"
        )

    system_prompt = (
        "You are an operational assistant for AROL capping machines. "
        "Answer using the machine data provided (alarms, telemetry, tickets), "
        "and the manual guidance section if present. "
        "Be concise and specific. Reference alarm codes and ticket IDs. "
        "Write directly to the user; never mention that data was 'provided' or "
        "'available to you'. "
        "When the question references a specific ID (e.g. an alarm ID like 'ALM-0016' or a "
        "ticket ID), find that EXACT ID in the data before answering. Do not answer about a "
        "different ID, and do not claim an ID doesn't exist without checking the full list "
        "of IDs shown to you. "
    )

    user_prompt = f"{data}{diagnosis_context}\n\nQuestion: {question}"

    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        think=False,
    )

    return {"answer": response["message"]["content"]}