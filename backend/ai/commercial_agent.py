import ollama

from core.models import Order, Quote, QuoteRevision

CHAT_MODEL = "qwen3.5:9b"

def gather_commercial_data(company):
    """
        Gather company's orders and quotes as a readable text
    """

    gathered_data = []

    orders = Order.objects.filter(company=company)
    gathered_data.append(f"ORDERS ({orders.count()}):")

    for order in orders:
        gathered_data.append(
            f"- {order.order_id}: status={order.order_status}, "
            f"shipment={order.shipment_status}, ordered={order.order_date}, "
            f"expected={order.expected_delivery_date}, from quote {order.quote_id}. "
            f"Notes: {order.notes}"
        )

    quotes = Quote.objects.filter(company=company)

    gathered_data.append(f"\nQUOTES ({quotes.count()}):")

    for quote in quotes:

        # Highest Revision Number is First --> latest (the current last)
        latest = (QuoteRevision.objects.filter(quote=quote)
                  .order_by("-revision_number").first()
        )
        
        rev_info = ""
        if latest:
            rev_info = (f" latest revision {latest.revision_number} "
                        f"({latest.revision_status}), discount {latest.discount_rate}")
        gathered_data.append(
            f"- {quote.quote_id}: {quote.description}, valid until {quote.valid_until}.{rev_info}"
        )

    return "\n".join(gathered_data)


def answer_commercial(company, question):
    """Commercial Agent: answer about the company's quotes and orders."""
    data = gather_commercial_data(company)

    system_prompt = (
        "You are a commercial assistant for AROL customers. "
        "Answer the user's question using ONLY the order and quote data provided. "
        "If the data doesn't contain the answer, say so plainly. "
        "Be concise and refer to specific order/quote IDs."
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