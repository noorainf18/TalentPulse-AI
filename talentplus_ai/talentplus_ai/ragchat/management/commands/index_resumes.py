from django.core.management.base import BaseCommand

from talentplus_ai.ragchat.services.indexer import index_candidates


class Command(BaseCommand):
    help = "Index candidate resumes into ChromaDB for RAG chatbot."

    def add_arguments(self, parser):
        parser.add_argument("--candidate-id", type=str, required=False)

    def handle(self, *args, **options):
        candidate_id = options.get("candidate_id")
        result = index_candidates(candidate_id=candidate_id)
        self.stdout.write(
            self.style.SUCCESS(
                f"Indexed candidates={result['candidates_indexed']} chunks={result['chunks_indexed']}"
            )
        )
