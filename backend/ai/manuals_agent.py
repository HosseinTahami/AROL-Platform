import ollama
from pgvector.django import CosineDistance

from core.models import DocChunk

CHAT_MODEL = "qwen3.5:9b"
EMBED_MODEL = "nomic-embed-text"

def retrive_chunks(machine, query, top_k=5):
    """
        Finding the most relevant manul for a machine + query.
    """

    qvec = ollama.embeddings(model=EMBED_MODEL, prompt=query)["embedding"]
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
        "You are a technical assistant for AROL capping machines. "
        "Answer the user's question using ONLY the manual excerpts provided. "
        "If the excerpts don't contain the answer, say so plainly. "
        "Cite the page numbers you used, like (page 98). "
        "Be concise and practical."
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