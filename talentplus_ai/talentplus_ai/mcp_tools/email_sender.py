"""
MCP Tool 3 — email_sender
File:   mcp_tools/email_sender.py
Folder: mcp_tools/

Sends personalised emails to candidates via Resend.
This MCP tool exposes email-sending as a standalone callable for any
external MCP-compatible client. The agent pipeline uses email_node.py
directly (which has richer screening/rejection templates). This tool
is for ad-hoc or externally-triggered outreach.

Input:  to_email, subject, body, email_type
Output: {"status": "sent"|"failed", "email_id": str, "message": str}

Fix applied:
  Removed unused `from core.exceptions import EmailSendError` import.
  EmailSendError was never raised — the function returns a dict on
  failure rather than raising. The import was dead code.

Example:
    email_sender(
        to_email="gaurav@example.com",
        subject="You've been shortlisted!",
        body="<p>Great work on your GitHub.</p>",
        email_type="screening"
    )
    → {"status": "sent", "email_id": "res_abc123", "email_type": "screening", ...}
"""

import logging
from django.conf import settings
import resend

logger = logging.getLogger(__name__)


def email_sender(
    to_email: str,
    subject: str,
    body: str,
    email_type: str = "custom",
) -> dict:
    """
    Sends an HTML email via Resend API and returns a confirmation dict.

    Args:
        to_email:   Recipient email address
        subject:    Email subject line
        body:       Email body — HTML or plain text (auto-wrapped in HTML if plain)
        email_type: "screening" | "rejection" | "custom" — used for tracking tags

    Returns:
        {"status": "sent", "email_id": str, "message": str, "email_type": str}
        {"status": "failed", "email_id": None, "message": str, "email_type": str}
    """
    logger.info("[email_sender] Sending '%s' email to %s", email_type, to_email)

    if not to_email or "@" not in to_email:
        return {"status": "failed", "message": "Invalid email address provided."}

    if not subject or not body:
        return {"status": "failed", "message": "Subject and body are required."}

    try:
        resend.api_key = settings.RESEND_API_KEY

        # Wrap plain-text body in minimal HTML if it contains no HTML tags
        html_body = (
            body if "<" in body
            else f"<div style='font-family:Arial,sans-serif;line-height:1.6'>{body}</div>"
        )

        params = {
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
            "tags": [
                {"name": "email_type", "value": email_type},
                {"name": "source",     "value": "talentpulse_ai"},
            ],
        }

        response = resend.Emails.send(params)
        email_id = response.get("id", "unknown")

        logger.info("[email_sender] Email sent. ID: %s", email_id)
        return {
            "status":     "sent",
            "email_id":   email_id,
            "message":    f"Email successfully sent to {to_email}.",
            "email_type": email_type,
        }

    except Exception as exc:
        error_msg = f"Resend API error: {exc}"
        logger.error("[email_sender] %s", error_msg)
        return {
            "status":     "failed",
            "email_id":   None,
            "message":    error_msg,
            "email_type": email_type,
        }