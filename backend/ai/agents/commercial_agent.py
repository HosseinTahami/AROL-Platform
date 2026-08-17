import ollama

from core.models import Order, OrderLine, Quote, QuoteRevision, QuoteLine

CHAT_MODEL = "qwen3.5:9b"


def gather_commercial_data(company):

    """
    Gather company's full commercial picture as readable text:
    every quote with its complete revision history and line items,
    and every order with its fulfillment detail.
    """
    gathered_data = []

    
    quotes = Quote.objects.filter(company=company)
    gathered_data.append(f"QUOTES ({quotes.count()}):")

    for quote in quotes:
        gathered_data.append(
            f"\n- Quote {quote.quote_id}: {quote.description} "
            f"(currency {quote.currency}, created {quote.created_at}, "
            f"valid until {quote.valid_until})"
        )

        
        revisions = QuoteRevision.objects.filter(quote=quote).order_by("revision_number")
        highest_number = revisions.last() 

        for rev in revisions:
            is_current = (rev == highest_number)
            marker = "[CURRENT]" if is_current else "[superseded]"
            gathered_data.append(
                f"    Revision {rev.revision_number} {marker}: "
                f"status={rev.revision_status}, discount={rev.discount_rate}, "
                f"issued={rev.issued_at}. "
                f"What changed: {rev.change_summary or 'n/a'}"
            )

            lines_for_rev = QuoteLine.objects.filter(quote_revision=rev)
            for line in lines_for_rev:
                machine_note = f" (machine {line.machine_id})" if line.machine_id else ""
                gathered_data.append(
                    f"      - {line.quote_line_id}: {line.description}, "
                    f"price={line.price}{machine_note}"
                )

    
    orders = Order.objects.filter(company=company)
    gathered_data.append(f"\nORDERS ({orders.count()}):")

    for order in orders:
        gathered_data.append(
            f"\n- Order {order.order_id}: status={order.order_status}, "
            f"shipment={order.shipment_status}, ordered={order.order_date}, "
            f"expected_delivery={order.expected_delivery_date}, "
            f"from quote {order.quote_id}, currency={order.currency}. "
            f"Notes: {order.notes or 'n/a'}"
        )
        order_lines = OrderLine.objects.filter(order=order)
        for ol in order_lines:
            gathered_data.append(
                f"    - line {ol.order_line_id}: {ol.fulfillment_status}"
            )

    return "\n".join(gathered_data)


def answer_commercial(company, question):
    """Commercial Agent: answer about the company's quotes and orders,
    including negotiation history and line-item detail."""
    data = gather_commercial_data(company)

    system_prompt = (
        "You are a commercial assistant for AROL customers. "
        "Answer the user's question using only the order and quote records available "
        "to you. The quote records include the FULL revision history of each "
        "negotiation, oldest first, with the current (highest-numbered) revision "
        "marked [CURRENT]. Use this history to explain how a negotiation evolved if "
        "asked (e.g. what changed between revisions, discount progression).\n\n"
        "Response style:\n"
        "- Answer like a knowledgeable colleague replying in a chat, not like a "
        "written report. A few sentences or a short list is usually enough.\n"
        "- If the question is about ONE quote or order, answer only about that one - "
        "do not summarize every other quote unless asked.\n"
        "- If the question is broad (e.g. 'how are our negotiations going'), give a "
        "brief overview and offer to go deeper on any one of them, rather than "
        "writing out the full history of every quote.\n"
        "- Mention specific IDs only when they help the user act (an order ID, a "
        "quote ID) - do not cite individual line-item IDs like 'QLN-0004' unless "
        "the user specifically asks about line items.\n\n"
        "If the records don't contain the answer, say so plainly. Write directly to "
        "the user as a finished answer: never mention that data was 'provided', "
        "'given', or 'available to you' - just state the facts directly."
    )

    user_prompt = (
        f"Commercial data for company {company.company_id}:\n\n"
        f"{data}\n\n"
        f"Question: {question}"
    )

    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        think=False,
    )

    return {"answer": response["message"]["content"]}