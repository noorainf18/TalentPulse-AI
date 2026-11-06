"""
Django Management Command — show_results
=========================================

Reads evaluation results from the database and prints a summary table.

Usage:
  python manage.py show_results
  python manage.py show_results --status screening_sent
  python manage.py show_results --min-score 80
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count


class Command(BaseCommand):
    help = "Display candidate evaluation results in the terminal."

    def add_arguments(self, parser):
        parser.add_argument(
            "--status",
            type=str,
            default="",
            help="Filter by status: pending, screening_sent, rejected, borderline, hired, error.",
        )
        parser.add_argument(
            "--min-score",
            type=int,
            default=0,
            help="Only show candidates with score >= this value.",
        )

    def handle(self, *args, **options):
        from talentplus_ai.candidates.models import Candidate, CandidateEvaluation

        status_filter = (options.get("status") or "").strip()
        min_score = int(options.get("min_score") or 0)

        allowed_status = {
            "pending",
            "screening_sent",
            "rejected",
            "borderline",
            "hired",
            "error",
        }
        if status_filter and status_filter not in allowed_status:
            raise CommandError(
                f"Invalid --status {status_filter!r}. Use one of: {', '.join(sorted(allowed_status))}"
            )

        qs = CandidateEvaluation.objects.select_related("candidate").order_by("-score")

        if status_filter:
            qs = qs.filter(status=status_filter)
        if min_score > 0:
            qs = qs.filter(score__gte=min_score)

        evaluations = list(qs)

        if not evaluations:
            self.stdout.write(self.style.WARNING("No evaluations found matching your filters."))
            total = CandidateEvaluation.objects.count()
            total_cand = Candidate.objects.count()
            self.stdout.write(f"Total candidates in DB: {total_cand}")
            self.stdout.write(f"Total evaluations in DB: {total}")
            if total_cand > total:
                self.stdout.write(
                    self.style.WARNING(
                        f"{total_cand - total} candidate(s) have no evaluation — "
                        "run: python manage.py run_screening"
                    )
                )
            return

        self.stdout.write(f"\n{'═' * 80}")
        self.stdout.write("  TALENTPLUS AI — CANDIDATE EVALUATION RESULTS")
        filter_desc = []
        if status_filter:
            filter_desc.append(f"status={status_filter}")
        if min_score > 0:
            filter_desc.append(f"min_score={min_score}")
        if filter_desc:
            self.stdout.write(f"  Filters: {', '.join(filter_desc)}")
        self.stdout.write(f"{'═' * 80}\n")

        self.stdout.write(
            f"  {'Name':<22} {'Score':>6} {'Label':<20} {'Status':<16} {'Email Sent':<10}"
        )
        self.stdout.write("  " + "─" * 76)

        status_colours = {
            "screening_sent": self.style.SUCCESS,
            "borderline": self.style.WARNING,
            "rejected": self.style.ERROR,
            "pending": lambda x: x,
            "hired": self.style.SUCCESS,
            "error": self.style.ERROR,
        }

        label_map = {
            "Strong Match": self.style.SUCCESS,
            "Hidden Gem": self.style.SUCCESS,
            "Promising": self.style.WARNING,
            "Needs Development": self.style.WARNING,
            "Not a Fit": self.style.ERROR,
        }

        for ev in evaluations:
            label = self._get_label(ev.score)
            colour = status_colours.get(ev.status, lambda x: x)
            label_colour = label_map.get(label, lambda x: x)
            email_icon = "✓" if ev.email_sent else "–"

            line = (
                f"  {ev.candidate.name:<22} "
                f"{ev.score:>6} "
                f"{label_colour(label):<20} "
                f"{colour(ev.status):<16} "
                f"{email_icon:<10}"
            )
            self.stdout.write(line)

        self.stdout.write(f"\n  Total: {len(evaluations)} candidate(s)")

        self.stdout.write("")
        status_counts = (
            CandidateEvaluation.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        self.stdout.write("  Status breakdown:")
        for row in status_counts:
            self.stdout.write(f"    {row['status']:<20} {row['count']}")
        self.stdout.write("")

    @staticmethod
    def _get_label(score: int) -> str:
        if score >= 85:
            return "Strong Match"
        if score >= 70:
            return "Hidden Gem"
        if score >= 60:
            return "Promising"
        if score >= 45:
            return "Needs Development"
        return "Not a Fit"
