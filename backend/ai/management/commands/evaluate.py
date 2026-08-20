import json
from pathlib import Path

import ollama
from pgvector.django import CosineDistance
from django.core.management.base import BaseCommand

from core.models import Machine, DocChunk, User
from ai.orchestrator.graph import graph as orchestrator_graph
from ai.orchestrator.graph import planner as graph_planner

EMBED_MODEL = "nomic-embed-text"
JUDGE_MODEL = "qwen3.5:9b"


def run_orchestrator(user, machine, question):
    machine_id = machine.machine_id if machine else ""
    return orchestrator_graph.invoke({
        "question": question, "user_id": user.id, "machine_id": machine_id,
        "refused": False, "refusal_reason": "", "agents_to_call": [],
        "agent_results": {}, "final_answer": "", "trace": [],
    })


def judge(question, answer, reference):


    """
        LLM-as-judge:
          score a generated answer against ground truth.

          1 - Poor
          5 - Excellent
    """


    system_prompt = (
        "You are grading an AI assistant's answer for correctness and faithfulness "
        "against a REFERENCE (ground truth). Score 1-5:\n"
        "5 = fully correct and faithful, no invented facts\n"
        "3 = partially correct or missing key information\n"
        "1 = incorrect or contains unsupported facts\n"
        'Respond with ONLY JSON: {"score": <1-5>, "reason": "<one sentence>"}'
    )

    user_prompt = f"Question: {question}\n\nReference: {reference}\n\nAnswer: {answer}"

    response = ollama.chat(
        model=JUDGE_MODEL,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_prompt}],
        think=False,
    )

    try:
        result = json.loads(response["message"]["content"].strip())
        return int(result["score"]), result.get("reason", "")

    except (json.JSONDecodeError, KeyError, ValueError):
        return None, "judge output unparseable"


def eval_routing(path):
    cases = json.loads(Path(path).read_text())
    correct, per_agent, misroutes = 0, {}, []
    for c in cases:
        got = graph_planner({"question": c["question"], "trace": []})["agents_to_call"]
        expected = c["expected_agent"]
        ok = expected in got
        correct += ok
        per_agent.setdefault(expected, [0, 0])
        per_agent[expected][1] += 1
        per_agent[expected][0] += ok
        if not ok:
            misroutes.append((c["question"], expected, got))
    return {
        "total": len(cases), "correct": correct,
        "per_agent": per_agent, "misroutes": misroutes,
    }


def eval_multi_agent(path):
    cases = json.loads(Path(path).read_text())
    results = []
    for c in cases:
        question = c["question"]
        expected_set = set(c["expected_agents"])
        got = set(graph_planner({"question": question, "trace": []})["agents_to_call"])
        results.append((question, expected_set, got, expected_set.issubset(got)))
    return results


def eval_rag_retrieval(path, k):
    cases = json.loads(Path(path).read_text())
    hits, reciprocal_ranks = 0, []
    for c in cases:
        qvec = ollama.embeddings(model=EMBED_MODEL, prompt=c["question"])["embedding"]
        m = Machine.objects.get(serial_number=c["machine_serial"])
        results = list(DocChunk.objects.filter(machine=m)
                        .order_by(CosineDistance("embedding", qvec))[:k]
                        .values_list("id", flat=True))
        if c["chunk_id"] in results:
            hits += 1
            reciprocal_ranks.append(1.0 / (results.index(c["chunk_id"]) + 1))
        else:
            reciprocal_ranks.append(0.0)
    return {
        "total": len(cases), "hits": hits, "k": k,
        "mrr": sum(reciprocal_ranks) / len(cases) if cases else 0,
    }


def eval_answer_quality(path):
    cases = json.loads(Path(path).read_text())
    user = User.objects.filter(visibility="full", company__company_id="CMP-001").first()
    scores, low_scores = [], []
    for c in cases:
        machine = Machine.objects.filter(serial_number=c["machine_serial"]).first()
        result = run_orchestrator(user, machine, c["question"])
        score, reason = judge(c["question"], result["final_answer"], c["reference_fact"])
        if score is not None:
            scores.append(score)
            if score <= 3:
                low_scores.append((c["question"], score, reason))
    return {"scores": scores, "low_scores": low_scores}


class Command(BaseCommand):
    
    help = "Evaluate orchestrator routing and agent answer quality."

    def add_arguments(self, parser):
        parser.add_argument("--routing", default="evaluation/eval_questions.json")
        parser.add_argument("--rag", default="evaluation/rag_questions.json")
        parser.add_argument("--answers", default="evaluation/answer_questions.json")
        parser.add_argument("--multi-agent", default="evaluation/multi_agent_questions.json")
        parser.add_argument("--k", type=int, default=5)

    def handle(self, *args, **options):
        routing = eval_routing(options["routing"])
        multi = eval_multi_agent(options["multi_agent"])
        rag = eval_rag_retrieval(options["rag"], options["k"])
        answers = eval_answer_quality(options["answers"])

        print("\nPILLAR 1 - ORCHESTRATOR")
        print(f"  Routing accuracy: {routing['correct']}/{routing['total']} "
              f"= {100*routing['correct']/routing['total']:.1f}%")
        for agent, (c, t) in routing["per_agent"].items():
            print(f"    {agent:>12}: {c}/{t} = {100*c/t:.0f}%")
        for q, exp, got in routing["misroutes"]:
            print(f"    miss: expected {exp}, got {got}: {q}")

        multi_correct = sum(1 for *_, ok in multi if ok)
        print(f"  Multi-agent coordination: {multi_correct}/{len(multi)}")
        for q, exp, got, ok in multi:
            mark = "OK" if ok else "MISS"
            print(f"    [{mark}] expected {exp}, got {got}: {q}")

        print("\nPILLAR 2 - AGENT / ANSWER QUALITY")
        print(f"  RAG Recall@{rag['k']}: {rag['hits']}/{rag['total']} "
              f"= {100*rag['hits']/rag['total']:.1f}%, MRR={rag['mrr']:.3f}")

        if answers["scores"]:
            avg = sum(answers["scores"]) / len(answers["scores"])
            print(f"  Answer quality (LLM-judge): {avg:.2f}/5 "
                  f"over {len(answers['scores'])} cases")
            for q, s, r in answers["low_scores"]:
                print(f"    [{s}/5] {q}\n        reason: {r}")
        print()