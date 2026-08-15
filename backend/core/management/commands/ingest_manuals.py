from pathlib import Path

import ollama, pypdf

from django.core.management.base import BaseCommand, CommandError

from core.models import Machine, DocChunk

from pathlib import Path



class Command(BaseCommand):

    help = """
            - Read manual PDFss
            - chunk PDFs
            - Embed chunk
            - Store them per machine
        """

    def add_arguments(self, parser):
        parser.add_argument("--dir", type=str, required=True,
                            help="Folder containing the manual PDFs")

    def handle(self, *args, **options):
        folder = Path(options["dir"])
        if not folder.is_dir():
            raise CommandError(f"Not a folder: {folder}")

        pdfs = sorted(folder.glob("*.pdf"))
        self.stdout.write(f"Found {len(pdfs)} PDF files")

        for pdf_path in pdfs:
            serial = pdf_path.name.split("_")[0]   # "15610_manual_EN.pdf" -> "15610"
            machine = Machine.objects.filter(serial_number=serial).first()
            if machine is None:
                self.stdout.write(self.style.WARNING(
                    f"  skip {pdf_path.name}: no machine with serial {serial}"))
                continue

            # Clear old chunks for this machine (re-runnable)
            DocChunk.objects.filter(machine=machine, source_file=pdf_path.name).delete()

            self.ingest_pdf(pdf_path, machine)

        self.stdout.write(self.style.SUCCESS("Manual ingestion complete."))

    def ingest_pdf(self, pdf_path, machine):
        reader = pypdf.PdfReader(str(pdf_path))
        chunk_index = 0

        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            for chunk_text in self.chunk_page(text):
                embedding = ollama.embeddings(
                    model="nomic-embed-text", prompt=chunk_text
                )["embedding"]
                DocChunk.objects.create(
                    machine=machine,
                    source_file=pdf_path.name,
                    page_num=page_num,
                    chunk_index=chunk_index,
                    content=chunk_text,
                    embedding=embedding,
                )
                chunk_index += 1

        self.stdout.write(self.style.SUCCESS(
            f"  {pdf_path.name} -> {machine.serial_number}: {chunk_index} chunks"))

    def chunk_page(self, text, max_chars=600, overlap=150):
            """Split page text into overlapping chunks for better retrieval."""
            text = " ".join(text.split())  # normalize whitespace
            if not text:
                return []
            chunks = []
            start = 0
            while start < len(text):
                end = start + max_chars
                chunks.append(text[start:end])
                start = end - overlap  # step back by overlap for the next chunk
            return chunks