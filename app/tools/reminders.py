import logging

from postgrest.exceptions import APIError

from app.services.supabase.factory import get_supabase_client

logger = logging.getLogger(__name__)


def create_reminder(patient_id: str, appointment_id: str | None, reminder_type: str, scheduled_at: str) -> dict:
    """Schedule a reminder for a patient.

    Use this after a successful booking (an "appointment" reminder), or for
    a standalone nudge not tied to any specific appointment (e.g. a general
    "follow_up" or "document_pending" reminder), by passing appointment_id
    as None in that case.

    Args:
        patient_id: The patient's id (patient_profiles.id, not user_id).
        appointment_id: The appointment this reminder is about, or None if
            it isn't tied to a specific one.
        reminder_type: One of "appointment", "follow_up", "document_pending".
        scheduled_at: ISO 8601 timestamp for when this reminder should fire.

    Returns:
        The newly created reminders row as a dict, with status="pending".

    Raises:
        RuntimeError: If the insert fails, e.g. reminder_type isn't one of
            the allowed values.
    """
    client = get_supabase_client()
    try:
        response = client.table("reminders").insert({
            "patient_id": patient_id,
            "appointment_id": appointment_id,
            "reminder_type": reminder_type,
            "scheduled_at": scheduled_at,
        }).execute()
    except APIError as e:
        logger.error(f"Failed to create reminder for patient {patient_id}: {e}")
        raise RuntimeError(f"Failed to create reminder: {e}") from e
    return response.data[0]


def get_patient_reminders(patient_id: str) -> list[dict]:
    """List every reminder scheduled for a patient.

    Use this to show a patient their upcoming reminders, or to check whether
    one already exists before creating a duplicate.

    Args:
        patient_id: The patient's id (patient_profiles.id, not user_id).

    Returns:
        A list of reminders rows. Empty list if the patient has none.
    """
    client = get_supabase_client()
    try:
        response = client.table("reminders").select("*").eq("patient_id", patient_id).execute()
    except APIError as e:
        logger.error(f"Failed to fetch reminders for patient {patient_id}: {e}")
        raise RuntimeError(f"Failed to fetch reminders: {e}") from e
    return response.data


def mark_reminder_sent(reminder_id: str) -> dict:
    """Mark a reminder as sent.

    Use this after whatever notification mechanism actually delivers the
    reminder (email, SMS, in-app) has successfully done so — this function
    only updates the status, it doesn't send anything itself.

    Args:
        reminder_id: The reminders.id to update.

    Returns:
        The updated reminders row as a dict.

    Raises:
        RuntimeError: If the update fails, or no reminder with that id exists.
    """
    client = get_supabase_client()
    try:
        response = client.table("reminders").update({"status": "sent"}).eq("id", reminder_id).execute()
    except APIError as e:
        logger.error(f"Failed to mark reminder {reminder_id} as sent: {e}")
        raise RuntimeError(f"Failed to mark reminder as sent: {e}") from e
    if not response.data:
        raise RuntimeError(f"No reminder found with id {reminder_id}")
    return response.data[0]
