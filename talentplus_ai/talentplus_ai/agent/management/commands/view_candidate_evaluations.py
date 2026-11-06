"""
Django Management Command — view_candidate_evaluations
======================================================

Inspect rows from candidate_evaluations directly from terminal.

Usage:
  python manage.py view_candidate_evaluations
  python manage.py view_candidate_evaluations --status borderline
  python manage.py view_candidate_evaluations --candidate-id <uuid>
  python manage.py view_candidate_evaluations --limit 5 --json
"""

import json

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "View detailed rows from candidate_evaluations table."

    def add_arguments(self, parser):
        parser.add_argument(
            "--candidate-id",
            type=str,
            default="",
            help="Filter by candidate UUID.",
        )
        parser.add_argument(
            "--status",
            type=str,
            default="",
            help="Filter by evaluation status (pending, screening_sent, rejected, borderline, hired, error).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Max rows to display (default: 20).",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            default=False,
            help="Print result as JSON.",
        )

    def handle(self, *args, **options):
        from talentplus_ai.candidates.models import CandidateEvaluation

        candidate_id = (options.get("candidate_id") or "").strip()
        status_filter = (options.get("status") or "").strip()
        limit = int(options.get("limit") or 20)
        as_json = bool(options.get("json"))

        if limit <= 0:
            raise CommandError("--limit must be > 0")

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

        qs = CandidateEvaluation.objects.select_related("candidate").order_by("-updated_at")
        if candidate_id:
            qs = qs.filter(candidate__id=candidate_id)
        if status_filter:
            qs = qs.filter(status=status_filter)

        evaluations = list(qs[:limit])
        if not evaluations:
            self.stdout.write(self.style.WARNING("No candidate_evaluations rows found for given filters."))
            return

        payload = []
        for ev in evaluations:
            payload.append(
                {
                    "evaluation_id": str(ev.id),
                    "candidate_id": str(ev.candidate_id),
                    "candidate_name": ev.candidate.name,
                    "candidate_email": ev.candidate.email,
                    "status": ev.status,
                    "score": ev.score,
                    "technical_score": ev.technical_score,
                    "culture_score": ev.culture_score,
                    "experience_score": ev.experience_score,
                    "reasoning": ev.reasoning,
                    "github_evidence": ev.github_evidence,
                    "gap_analysis": ev.gap_analysis,
                    "trace_log": ev.trace_log,
                    "email_sent": ev.email_sent,
                    "feedback_thumbs_up": ev.feedback_thumbs_up,
                    "feedback_notes": ev.feedback_notes,
                    "evaluated_at": ev.evaluated_at.isoformat() if ev.evaluated_at else None,
                    "updated_at": ev.updated_at.isoformat() if ev.updated_at else None,
                }
            )

        if as_json:
            self.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
            return

        self.stdout.write(f"\nShowing {len(payload)} row(s) from candidate_evaluations:\n")
        for i, row in enumerate(payload, start=1):
            self.stdout.write("═" * 90)
            self.stdout.write(
                f"[{i}] {row['candidate_name']} <{row['candidate_email']}> | "
                f"Status={row['status']} | Score={row['score']}"
            )
            self.stdout.write(
                f"    Technical={row['technical_score']}  Culture={row['culture_score']}  "
                f"Experience={row['experience_score']}  EmailSent={row['email_sent']}"
            )
            self.stdout.write(
                f"    evaluation_id={row['evaluation_id']}  candidate_id={row['candidate_id']}"
            )
            self.stdout.write(
                f"    evaluated_at={row['evaluated_at']}  updated_at={row['updated_at']}"
            )
            self.stdout.write(f"    reasoning: {row['reasoning'] or ''}")
            self.stdout.write("    github_evidence:")
            self.stdout.write(f"{json.dumps(row['github_evidence'] or {}, indent=6, ensure_ascii=False)}")
            self.stdout.write("    gap_analysis:")
            self.stdout.write(f"{json.dumps(row['gap_analysis'] or {}, indent=6, ensure_ascii=False)}")
            self.stdout.write("    trace_log:")
            self.stdout.write(f"{json.dumps(row['trace_log'] or [], indent=6, ensure_ascii=False)}")
            if row["feedback_thumbs_up"] is not None or row["feedback_notes"]:
                self.stdout.write(
                    f"    feedback: thumbs_up={row['feedback_thumbs_up']} notes={row['feedback_notes'] or ''}"
                )
        self.stdout.write("═" * 90)
