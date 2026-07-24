import logging

import resend

from config import get_settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html: str) -> dict:
    """Send a transactional email via Resend. Deterministic — no LLM involved.

    Args:
        to: The recipient email address.
        subject: The email subject line.
        html: The email body as HTML.

    Returns:
        Resend's send response (contains the message id).

    Raises:
        RuntimeError: If Resend isn't configured, or the send fails.
    """
    settings = get_settings()
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY is not configured; cannot send email")

    resend.api_key = settings.resend_api_key
    try:
        result = resend.Emails.send({
            "from": settings.reminder_from_email,
            "to": [to],
            "subject": subject,
            "html": html,
        })
    except Exception as e:  # noqa: BLE001 - surface any Resend/transport failure uniformly
        logger.error(f"Failed to send email to {to}: {e}")
        raise RuntimeError(f"Failed to send email to {to}: {e}") from e

    logger.info(f"Sent email to {to} (subject={subject!r})")
    return result