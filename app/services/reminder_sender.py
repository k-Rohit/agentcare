"""Reminder sender — the background job that actually emails due reminders.

The Follow-up agent only *schedules* reminders (creates a `reminders` row with
`scheduled_at` = 24h before the appointment, status "pending"). This process is
what sends them: it finds reminders whose time has come and emails the patient.

Run it on a schedule (cron, a scheduled function, etc.), e.g. every 15 minutes:
    uv run python -m app.services.reminder_sender

For a demo you can just run it manually to send whatever is currently due.
"""

import logging
from datetime import datetime, timezone

from app.services.supabase.factory import get_supabase_client
from app.tools.appointments import get_appointment_details
from app.tools.patients import get_patient_email
from app.tools.reminders import mark_reminder_sent
from app.tools.notifications import send_email
from app.tools.audit import log_audit_event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _build_email(details: dict) -> tuple[str, str]:
    """Build (subject, html) for an appointment reminder from its details."""
    doctor = details.get("doctors", {}).get("name", "your doctor")
    start = details["appointment_slots"]["start_time"]
    when = datetime.fromisoformat(start).strftime("%A, %B %d at %I:%M %p").replace(" 0", " ")
    subject = "Appointment reminder — AgentCare"
    html = (
        f"<p>Hi,</p>"
        f"<p>This is a reminder of your upcoming appointment with "
        f"<strong>{doctor}</strong> on <strong>{when}</strong>.</p>"
        f"<p>If you need to reschedule or cancel, just log in to AgentCare.</p>"
        f"<p>— AgentCare</p>"
    )
    return subject, html


def send_due_reminders() -> int:
    """Find pending reminders whose scheduled_at has passed, email them, and
    mark them sent. Returns how many were sent."""
    client = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()

    due = (
        client.table("reminders")
        .select("*")
        .eq("status", "pending")
        .lte("scheduled_at", now)
        .execute()
        .data
    )
    logger.info(f"{len(due)} reminder(s) due")

    sent = 0
    for reminder in due:
        try:
            details = get_appointment_details(reminder["appointment_id"])
            if not details:
                logger.warning(f"Reminder {reminder['id']}: appointment not found, skipping")
                continue
            email = get_patient_email(reminder["patient_id"])
            if not email:
                logger.warning(f"Reminder {reminder['id']}: no patient email, skipping")
                continue

            subject, html = _build_email(details)
            send_email(email, subject, html)
            mark_reminder_sent(reminder["id"])
            log_audit_event(
                actor_id=None,  # sent by the system, not a user
                action="sent_reminder",
                entity_type="reminder",
                entity_id=reminder["id"],
            )
            sent += 1
        except Exception as e:  # noqa: BLE001 - one bad reminder shouldn't stop the rest
            logger.error(f"Failed to send reminder {reminder['id']}: {e}")

    logger.info(f"Sent {sent}/{len(due)} due reminder(s)")
    return sent


if __name__ == "__main__":
    send_due_reminders()