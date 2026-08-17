import ollama
from pgvector.django import CosineDistance

from core.models import DocChunk

CHAT_MODEL = "qwen3.5:9b"
EMBED_MODEL = "nomic-embed-text"

"""
    RAG: Retrive Augmented Generation

        - R: retrive_chunks method

        - AG: answer_from_manual

"""


def retrive_chunks(machine, query, top_k=5):
    """
        Finding the most relevant manul for a machine + query.
    """

    # Convert user's question with the same EMBED_MODEL
    qvec = ollama.embeddings(model=EMBED_MODEL, prompt=query)["embedding"]

    # order the result base on 2 vectors similarity 
    # similarity is measured base on the cosine of the angle
    # between the 2 vectors (text chunks & question)
    result = DocChunk.objects.filter(machine=machine).order_by(
        CosineDistance("embedding", qvec)
    )

    return list(result[:top_k])

def answer_from_manual(machine, question):
    """
        Manuals Agent answer a question using the machine's manual.
    """

    chunks = retrive_chunks(machine, question)

    if not chunks:
        return {
            "answer": "I did not find anything relevant in this machine's manual.",
            "sources": []
        }
    

    # Build the context block from retrieved chunks, with page labels.
    context = ""

    for chunk in chunks:
        context += f"[Page {chunk.page_num}] {chunk.content}\n\n"


    system_prompt = (
        "You are a technical troubleshooting assistant for AROL capping machines. "
        "You answer questions using ONLY the manual excerpts provided below - "
        "never use outside knowledge, even if you believe it to be correct.\n\n"
        "Rules:\n"
        "- If the excerpts do not contain enough information to answer, say so "
        "plainly instead of guessing.\n"
        "- Every claim you make must be traceable to a specific excerpt; cite the "
        "page number in parentheses immediately after the claim, e.g. (page 98).\n"
        "- If excerpts appear to conflict, point out the conflict rather than "
        "silently picking one.\n"
        "- Be concise: prefer short, numbered steps for procedures over long prose.\n"
        "- Do not invent part numbers, torque values, dimensions, or other specific "
        "figures that are not explicitly present in the excerpts."
    )

    user_prompt = (
        f"Manual excerpts for machine {machine.serial_number}:\n\n"
        f"{context}\n\n"
        f"Question: {question}"
    )

    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        think=False
    )

    return {
        "answer": response["message"]["content"],
        "sources": [
            {"page": c.page_num, "file": c.source_file} for c in chunks
        ],
    }