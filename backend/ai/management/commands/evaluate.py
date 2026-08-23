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


def load_benchmark(path):
    """Read a benchmark JSON file and return its list of test cases."""
    text = Path(path).read_text()
    cases = json.loads(text)
    return cases


def run_orchestrator(user, machine, question):
    """Run one question through the real, live orchestrator graph."""
    machine_id = machine.machine_id if machine else ""
    starting_state = {
        "question": question,
        "user_id": user.id,
        "machine_id": machine_id,
        "refused": False,
        "refusal_reason": "",
        "agents_to_call": [],
        "agent_results": {},
        "final_answer": "",
        "trace": [],
    }
    return orchestrator_graph.invoke(starting_state)


def judge(question, answer, reference):
    """
    LLM-as-judge: score a generated answer against a known-true reference.
      5 = fully correct and faithful
      3 = partially correct or missing key information
      1 = incorrect or contains unsupported facts
    Returns (score, reason). score is None if the judge's reply could not
    be parsed as valid JSON.
    """
    system_prompt = """You are grading an AI assistant's answer for correctness and faithfulness against a REFERENCE (ground truth). Score 1-5:
5 = fully correct and faithful, no invented facts
3 = partially correct or missing key information
1 = incorrect or contains unsupported facts
Respond with ONLY JSON: {"score": <1-5>, "reason": "<one sentence>"}"""

    user_prompt = f"Question: {question}\n\nReference: {reference}\n\nAnswer: {answer}"

    response = ollama.chat(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        think=False,
    )

    raw_reply = response["message"]["content"].strip()
    try:
        result = json.loads(raw_reply)
        score = int(result["score"])
        reason = result.get("reason", "")
        return score, reason
    except (json.JSONDecodeError, KeyError, ValueError):
        return None, "judge output unparseable"


# ---------------------------------------------------------------- #
# Pillar 1: does the orchestrator route to the right specialist(s)?
# ---------------------------------------------------------------- #

def eval_routing(path):
    """For each question, does the planner's choice include the expected agent?"""
    cases = load_benchmark(path)

    total_correct = 0
    per_agent_stats = {}   # e.g. {"manuals": {"correct": 8, "total": 8}}
    misroutes = []

    for case in cases:
        question = case["question"]
        expected_agent = case["expected_agent"]

        planner_state = {"question": question, "trace": []}
        chosen_agents = graph_planner(planner_state)["agents_to_call"]

        is_correct = expected_agent in chosen_agents

        if expected_agent not in per_agent_stats:
            per_agent_stats[expected_agent] = {"correct": 0, "total": 0}
        per_agent_stats[expected_agent]["total"] += 1
        if is_correct:
            per_agent_stats[expected_agent]["correct"] += 1
            total_correct += 1
        else:
            misroutes.append({
                "question": question,
                "expected": expected_agent,
                "got": chosen_agents,
            })

    return {
        "total_cases": len(cases),
        "total_correct": total_correct,
        "per_agent_stats": per_agent_stats,
        "misroutes": misroutes,
    }


def eval_multi_agent(path):
    """For cross-domain questions, does the planner select every REQUIRED
    specialist? (Picking an extra, reasonable specialist is not penalized.)"""
    cases = load_benchmark(path)

    results = []
    for case in cases:
        question = case["question"]
        expected_agents = set(case["expected_agents"])

        planner_state = {"question": question, "trace": []}
        chosen_agents = set(graph_planner(planner_state)["agents_to_call"])

        passed = expected_agents.issubset(chosen_agents)
        results.append({
            "question": question,
            "expected": expected_agents,
            "got": chosen_agents,
            "passed": passed,
        })

    return results


# ---------------------------------------------------------------- #
# Pillar 2: is the AGENTS' actual output correct?
# ---------------------------------------------------------------- #

def eval_rag_retrieval(path, k):
    """For each question, is the manual chunk it was generated from
    actually retrieved in the top k search results?"""
    cases = load_benchmark(path)

    hits = 0
    reciprocal_ranks = []

    for case in cases:
        question = case["question"]
        correct_chunk_id = case["chunk_id"]
        machine = Machine.objects.get(serial_number=case["machine_serial"])

        query_vector = ollama.embeddings(model=EMBED_MODEL, prompt=question)["embedding"]

        top_chunk_ids = list(
            DocChunk.objects.filter(machine=machine)
            .order_by(CosineDistance("embedding", query_vector))[:k]
            .values_list("id", flat=True)
        )

        if correct_chunk_id in top_chunk_ids:
            hits += 1
            rank = top_chunk_ids.index(correct_chunk_id) + 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)

    total = len(cases)
    mrr = sum(reciprocal_ranks) / total if total else 0

    return {"total_cases": total, "hits": hits, "k": k, "mrr": mrr}


def eval_answer_quality(path):
    """Run each question through the REAL orchestrator, then have the
    judge score the real answer against a database-derived reference fact."""
    cases = load_benchmark(path)

    # All answer-quality questions are about company CMP-001, so the test
    # user must belong to that same company (see documentation for why).
    test_user = User.objects.filter(
        visibility="full", company__company_id="CMP-001"
    ).first()

    scores = []
    weak_cases = []

    for case in cases:
        question = case["question"]
        reference_fact = case["reference_fact"]
        machine = Machine.objects.filter(serial_number=case["machine_serial"]).first()

        result = run_orchestrator(test_user, machine, question)
        generated_answer = result["final_answer"]

        score, reason = judge(question, generated_answer, reference_fact)

        if score is not None:
            scores.append(score)
            if score <= 3:
                weak_cases.append({"question": question, "score": score, "reason": reason})

    return {"scores": scores, "weak_cases": weak_cases}


# ---------------------------------------------------------------- #
# The command: run everything, then print one clean report
# ---------------------------------------------------------------- #

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
        multi_agent = eval_multi_agent(options["multi_agent"])
        rag = eval_rag_retrieval(options["rag"], options["k"])
        answers = eval_answer_quality(options["answers"])

        self.print_routing_report(routing)
        self.print_multi_agent_report(multi_agent)
        self.print_rag_report(rag)
        self.print_answer_quality_report(answers)

    def print_routing_report(self, routing):
        print("\nPILLAR 1 - ORCHESTRATOR")
        total = routing["total_cases"]
        correct = routing["total_correct"]
        percentage = 100 * correct / total
        print(f"  Routing accuracy: {correct}/{total} = {percentage:.1f}%")

        for agent_name, stats in routing["per_agent_stats"].items():
            agent_pct = 100 * stats["correct"] / stats["total"]
            print(f"    {agent_name:>12}: {stats['correct']}/{stats['total']} = {agent_pct:.0f}%")

        for miss in routing["misroutes"]:
            print(f"    miss: expected {miss['expected']}, got {miss['got']}: {miss['question']}")

    def print_multi_agent_report(self, results):
        passed_count = sum(1 for r in results if r["passed"])
        print(f"  Multi-agent coordination: {passed_count}/{len(results)}")
        for r in results:
            mark = "OK" if r["passed"] else "MISS"
            print(f"    [{mark}] expected {r['expected']}, got {r['got']}: {r['question']}")

    def print_rag_report(self, rag):
        print("\nPILLAR 2 - AGENT / ANSWER QUALITY")
        pct = 100 * rag["hits"] / rag["total_cases"]
        print(f"  RAG Recall@{rag['k']}: {rag['hits']}/{rag['total_cases']} = {pct:.1f}%, MRR={rag['mrr']:.3f}")

    def print_answer_quality_report(self, answers):
        if not answers["scores"]:
            return
        average_score = sum(answers["scores"]) / len(answers["scores"])
        print(f"  Answer quality (LLM-judge): {average_score:.2f}/5 over {len(answers['scores'])} cases")
        for weak in answers["weak_cases"]:
            print(f"    [{weak['score']}/5] {weak['question']}\n        reason: {weak['reason']}")
        print()