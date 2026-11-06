from django.core.management.base import BaseCommand

from talentplus_ai.ragchat.services.qa_chain import generate_answer
from talentplus_ai.ragchat.services.retriever import hybrid_retrieve


class Command(BaseCommand):
    help = "Test the end-to-end RAG QA chatbot (retrieve + Anthropic answer)."

    def add_arguments(self, parser):
        parser.add_argument("--question", type=str, required=True)
        parser.add_argument("--candidate-id", type=str, required=False)
        parser.add_argument("--top-k", type=int, required=False, default=6)

    def handle(self, *args, **options):
        question = options["question"]
        candidate_id = options.get("candidate_id")
        top_k = int(options.get("top_k") or 6)

        rows = hybrid_retrieve(question=question, top_k=top_k, candidate_id=candidate_id)
        answer, citations = generate_answer(question=question, retrieved_rows=rows)

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Answer"))
        self.stdout.write(answer)
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Citations"))
        for c in citations:
            self.stdout.write(f"- {c}")
        self.stdout.write("")

