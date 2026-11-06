"""
Run the full LangGraph screening pipeline for every candidate (synchronous CLI).

Usage:
  python manage.py run_screening
  python manage.py run_screening --candidate-id <uuid>
"""

import time

from django.core.management.base import BaseCommand

from talentplus_ai.agent.graph import run_screening as execute_screening_pipeline


class Command(BaseCommand):
    help = (
        "Run the full LangGraph screening pipeline for all pending evaluations. "
        "Executes synchronously in this process."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--candidate-id",
            type=str,
            default="",
            help="Run screening for a single candidate ID only.",
        )

    def handle(self, *args, **options):
        from talentplus_ai.candidates.models import CandidateEvaluation

        candidate_id_filter = options.get("candidate_id", "").strip()

        qs = CandidateEvaluation.objects.select_related("candidate").filter(status="pending")
        if candidate_id_filter:
            qs = qs.filter(candidate__id=candidate_id_filter)

        evaluations = list(qs.order_by("evaluated_at"))

        if not evaluations:
            self.stdout.write(self.style.WARNING(
                "No pending evaluations found. "
                "Ingest resumes first (e.g. python manage.py extract_resume_pdf)."
            ))
            return

        self.stdout.write(f"Screening {len(evaluations)} pending evaluation(s)…\n{'─' * 60}")

        results = []
        success_count = 0
        error_count = 0

        for evaluation in evaluations:
            candidate = evaluation.candidate
            self.stdout.write(
                f"\n▶ {candidate.name} ({candidate.email}) — role: {evaluation.target_role or 'General'}"
            )

            start = time.time()
            try:
                final_state = execute_screening_pipeline(
                    candidate_id=str(candidate.id),
                    evaluation_id=str(evaluation.id),
                )

                elapsed = round(time.time() - start, 1)
                score  = final_state.get("score", 0)
                label  = final_state.get("candidate_label", "Unknown")
                email_status = final_state.get("email_status", "skipped")
                err    = final_state.get("error")

                for step in final_state.get("trace_log") or []:
                    icon = "✓" if step.get("status") == "done" else "✗"
                    self.stdout.write(f"  {icon} [{step.get('step', '?')}] {step.get('message', '')}")

                if err:
                    self.stderr.write(self.style.ERROR(f"  ✗ Pipeline error: {err}"))
                    error_count += 1
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f"\n  Score: {score}/100 | Label: {label} | "
                        f"Email: {email_status} | {elapsed}s"
                    ))
                    results.append({
                        "name": candidate.name,
                        "email": candidate.email,
                        "role": evaluation.target_role or "General",
                        "score": score,
                        "label": label,
                        "email_status": email_status,
                    })
                    success_count += 1

            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"  ✗ Exception: {exc}"))
                error_count += 1

        self.stdout.write(f"\n{'═' * 60}")
        self.stdout.write(f"Done — {success_count} completed, {error_count} failed/skipped\n")

        if results:
            self.stdout.write(
                f"\n{'Name':<25} {'Role':<20} {'Score':>6} {'Label':<22} {'Email out':<12}"
            )
            self.stdout.write("─" * 88)
            for r in sorted(results, key=lambda x: x["score"], reverse=True):
                self.stdout.write(
                    f"{r['name'][:25]:<25} {r['role'][:20]:<20} {r['score']:>6} "
                    f"{r['label'][:22]:<22} {r['email_status']:<12}"
                )