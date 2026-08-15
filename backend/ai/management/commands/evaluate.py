import json
from pathlib import Path

import ollama
from pgvector.django import CosineDistance
from django.core.management.base import BaseCommand

from core.models import User, Machine, DocChunk
from ai.orchestrator import classify_question, orchestrate

EMBED_MODEL = "nomic-embed-text"

SECURITY_CASES = [
    ("full", "What alarms does this machine have?", False),
    ("technician", "What alarms does this machine have?", False),
    ("commercial", "What alarms does this machine have?", True),
    ("technician", "Are there open maintenance tickets?", False),
    ("commercial", "Are there open maintenance tickets?", True),
    ("full", "What orders do we have?", False),
    ("commercial", "What orders do we have?", False),
    ("technician", "What orders do we have?", True),
    ("commercial", "What was the latest quote revision?", False),
    ("technician", "When was the machine delivered and for how much?", True),
    ("full", "How do I fix low air pressure?", False),
    ("technician", "How do I replace a closure head?", False),
    ("commercial", "What safety precautions apply?", False),
]


class Command(BaseCommand):
    help = "Run the full evaluation suite against the frozen benchmark."

    def add_arguments(self, parser):
        parser.add_argument("--routing", default="evaluation/eval_questions.json")
        parser.add_argument("--rag", default="evaluation/rag_questions.json")
        parser.add_argument("--k", type=int, default=5)

    def handle(self, *args, **options):
        machine = Machine.objects.get(serial_number="15610")
        self.routing(options["routing"])
        self.security(machine)
        self.isolation()
        self.rag(options["rag"], options["k"])

    def routing(self, path):
        cases = json.loads(Path(path).read_text())
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n=== ROUTING ({len(cases)} questions) ==="))
        from collections import defaultdict
        per = defaultdict(lambda: [0, 0])
        correct, misroutes = 0, []
        for c in cases:
            got = classify_question(c["question"])
            ok = got == c["expected_agent"]
            correct += ok
            per[c["expected_agent"]][1] += 1
            per[c["expected_agent"]][0] += ok
            if not ok:
                misroutes.append((c["question"], c["expected_agent"], got))
        t = len(cases)
        self.stdout.write(self.style.SUCCESS(f"Overall: {correct}/{t} = {100*correct/t:.1f}%"))
        for agent, (c, tt) in per.items():
            self.stdout.write(f"  {agent:>12}: {c}/{tt} = {100*c/tt:.0f}%")
        for q, exp, got in misroutes:
            self.stdout.write(self.style.WARNING(f"    {exp}->{got}: {q}"))

    def security(self, machine):
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== SECURITY (visibility) ==="))
        correct = 0
        for vis, q, should in SECURITY_CASES:
            u = User.objects.filter(visibility=vis, company__isnull=False).first()
            ok = orchestrate(u, machine, q)["refused"] == should
            correct += ok
            if not ok:
                self.stdout.write(self.style.ERROR(f"  ✗ [{vis}] {q}"))
        t = len(SECURITY_CASES)
        self.stdout.write(self.style.SUCCESS(f"Security: {correct}/{t} = {100*correct/t:.0f}%"))

    def isolation(self):
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== COMPANY ISOLATION ==="))
        u = User.objects.filter(company__company_id="CMP-001", visibility="full").first()
        others = Machine.objects.exclude(company__company_id="CMP-001")
        correct = 0
        for m in others:
            if orchestrate(u, m, "How do I fix this?")["refused"]:
                correct += 1
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ LEAK: {m.machine_id}"))
        t = others.count()
        self.stdout.write(self.style.SUCCESS(f"Isolation: {correct}/{t} = {100*correct/t:.0f}%"))

    def rag(self, path, k):
        cases = json.loads(Path(path).read_text())
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n=== RAG RETRIEVAL ({len(cases)} questions, k={k}) ==="))
        hits, rr = 0, []
        for c in cases:
            qvec = ollama.embeddings(model=EMBED_MODEL, prompt=c["question"])["embedding"]
            m = Machine.objects.get(serial_number=c["machine_serial"])
            results = list(DocChunk.objects.filter(machine=m)
                           .order_by(CosineDistance("embedding", qvec))[:k]
                           .values_list("id", flat=True))
            if c["chunk_id"] in results:
                hits += 1
                rr.append(1.0 / (results.index(c["chunk_id"]) + 1))
            else:
                rr.append(0.0)
        t = len(cases)
        self.stdout.write(self.style.SUCCESS(f"Recall@{k}: {hits}/{t} = {100*hits/t:.1f}%"))
        self.stdout.write(self.style.SUCCESS(f"MRR: {sum(rr)/t:.3f}"))