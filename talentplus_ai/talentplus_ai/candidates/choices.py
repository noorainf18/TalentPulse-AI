"""Shared choice tuples for candidates app models."""

SENIORITY_CHOICES = [
    ("Junior", "Junior"),
    ("Mid", "Mid"),
    ("Senior", "Senior"),
    ("Lead", "Lead"),
]

PRIORITY_CHOICES = [
    ("High", "High"),
    ("Medium", "Medium"),
    ("Low", "Low"),
]

CANDIDATE_EVALUATION_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("screening_sent", "Screening Sent"),
    ("rejected", "Rejected"),
    ("hired", "Hired"),
    ("borderline", "Borderline"),
    ("error", "Error"),
]
