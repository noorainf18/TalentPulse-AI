from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid

from .choices import (
    CANDIDATE_EVALUATION_STATUS_CHOICES,
    PRIORITY_CHOICES,
    SENIORITY_CHOICES,
)


class TeamProfile(models.Model):
    role = models.CharField(max_length=200)
    seniority_level = models.CharField(max_length=50, choices=SENIORITY_CHOICES)
    department = models.CharField(max_length=100)
    current_skills = ArrayField(models.CharField(max_length=100), default=list)
    missing_skills = ArrayField(models.CharField(max_length=100), default=list)
    culture_values = ArrayField(models.CharField(max_length=200), default=list)
    hiring_priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="Medium")
    headcount_needed = models.PositiveIntegerField(default=1)
    min_experience_years = models.PositiveIntegerField(default=0)
    preferred_experience_years = models.PositiveIntegerField(default=2)
    tech_stack_focus = models.TextField(blank=True)
    team_size = models.PositiveIntegerField(null=True, blank=True)
    remote_friendly = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidates_teamprofile"
        ordering = ["-hiring_priority", "role"]

    def __str__(self):
        return f"{self.role} ({self.seniority_level}) — {self.department}"


class JobDescription(models.Model):
    title = models.CharField(max_length=200)
    department = models.CharField(max_length=100)
    team_profile = models.ForeignKey(
        TeamProfile, on_delete=models.SET_NULL, null=True, related_name="job_descriptions",
    )
    description = models.TextField()
    responsibilities = ArrayField(models.TextField(), default=list)
    required_skills = ArrayField(models.CharField(max_length=100), default=list)
    preferred_skills = ArrayField(models.CharField(max_length=100), default=list)
    required_experience_years = models.PositiveIntegerField(default=0)
    employment_type = models.CharField(max_length=50, default="Full-Time")
    location = models.CharField(max_length=200, blank=True)
    salary_range_lpa = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidates_jobdescription"
        ordering = ["-is_active", "title"]

    def __str__(self):
        return f"{self.title} — {self.department}"


class Candidate(models.Model):
    """
    Stores all structured data extracted from the uploaded PDF resume.
    Each row represents one candidate (identified by email).

    skills is a JSONField storing [{category, skills[]}] objects,
    preserving the resume's own section headings exactly as written.
    Example:
      [
        {"category": "Programming & Frameworks", "skills": ["Python", "Django", ...]},
        {"category": "AI, ML & Generative AI",  "skills": ["LangChain", "RAG", ...]},
      ]
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ── Core identity
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=30, blank=True, null=True)

    # ── Online profiles
    github_url = models.URLField(blank=True, null=True)
    portfolio_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    raw_github_username = models.CharField(max_length=100, blank=True)

    # ── Extracted resume content
    summary = models.TextField(blank=True)
    skills = models.JSONField(default=list)           # [{category, skills[]}]
    experience = models.JSONField(default=list)
    projects = models.JSONField(default=list)
    education = models.JSONField(default=list)
    certifications = models.JSONField(default=list)
    achievements = models.JSONField(default=list)
    position_of_responsibility = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidates"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    def flat_skills(self) -> list:
        """Flat list of all skill strings — used by vectorizer and gap analysis."""
        flat = []
        for group in (self.skills or []):
            if isinstance(group, dict):
                flat.extend(group.get("skills") or [])
        return flat


class CandidateEvaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="evaluations",
    )
    job_description = models.ForeignKey(
        JobDescription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluations",
        help_text="Optional link for voice screening / JD-grounded questions.",
    )
    target_role = models.CharField(max_length=200, blank=True)
    resume_hash = models.CharField(max_length=64, blank=True)
    score = models.IntegerField(default=0)
    technical_score = models.IntegerField(default=0)
    culture_score = models.IntegerField(default=0)
    experience_score = models.IntegerField(default=0)
    reasoning = models.TextField()
    github_evidence = models.JSONField(null=True, blank=True)
    gap_analysis = models.JSONField(null=True, blank=True)
    trace_log = models.JSONField(default=list)
    status = models.CharField(
        max_length=30, choices=CANDIDATE_EVALUATION_STATUS_CHOICES, default="pending",
    )
    email_sent = models.BooleanField(default=False)
    feedback_thumbs_up = models.BooleanField(null=True, blank=True)
    feedback_notes = models.TextField(blank=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "candidate_evaluations"
        ordering = ["-score", "-evaluated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["candidate", "target_role"],
                name="unique_candidate_role_evaluation",
            )
        ]

    def __str__(self):
        return f"{self.candidate.name} — {self.target_role or 'General'} — Score: {self.score} ({self.status})"