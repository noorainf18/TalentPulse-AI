from django.db import models


class VoiceInterviewStatus(models.TextChoices):
    PENDING = "pending", "Pending"          # questions generated, invite not yet sent
    INVITED = "invited", "Invited"          # candidate email sent, waiting to join
    ACTIVE = "active", "Active"             # call in progress
    COMPLETED = "completed", "Completed"    # call ended, analysis done
    FAILED = "failed", "Failed"             # call errored or agent crashed
    SKIPPED = "skipped", "Skipped"          # recruiter manually skipped voice screen
    EXPIRED = "expired", "Expired"          # candidate never joined within window


class QuestionType(models.TextChoices):
    RESUME_GAP = "resume_gap", "Resume Gap"             # probes gap_analysis findings
    ROLE_TECHNICAL = "role_technical", "Role Technical" # JD required_skills depth
    CULTURE_FIT = "culture_fit", "Culture Fit"          # TeamProfile culture_values
    CLARIFICATION = "clarification", "Clarification"    # follow-up on vague answer