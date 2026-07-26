from datetime import datetime, timedelta
import logging

from langchain_core.messages import AIMessage

from app.agents.state import WorkflowState
from app.services.appointments import get_appointment_details
from app.tools.reminders import create_reminder
from app.tools.audit import log_audit_event
from app.services.workflow import update_workflow_run

logger = logging.getLogger(__name__)

REMINDER_LEAD_HOURS = 24

# Only an appointment that is still upcoming should get a reminder. A cancel sets
# the status to "cancelled" and a completed visit to "completed" — neither needs one.
ACTIVE_STATUSES = {"pending", "confirmed", "rescheduled"}


def followup_node(state: WorkflowState) -> dict:
    """Schedule a reminder for an upcoming appointment (deterministic — no LLM).

    Runs after the appointment step. If an appointment is still active this turn
    (booked or rescheduled), it creates a reminder row timed 24h before the
    appointment. It does NOT send an email — a separate reminder-sender process
    sends due reminders. It is a no-op for a status check, a document request, or
    a CANCELLED appointment (a cancel must never schedule a reminder).
    """
    appointment_id = state.get("appointment_id")
    workflow_run_id = state["workflow_run_id"]

    if not appointment_id:
        return {}  # nothing actionable this turn → no reminder to schedule

    details = get_appointment_details(appointment_id)
    if not details:
        logger.error(f"Follow-up: appointment {appointment_id} not found; skipping reminder")
        return {}

    # Don't remind about a cancelled/completed appointment (fixes: cancel was
    # still scheduling a reminder because appointment_id was set).
    if details.get("status") not in ACTIVE_STATUSES:
        return {}

    start_time = details["appointment_slots"]["start_time"]
    patient_id = state["patient_id"]

    # schedule the reminder for REMINDER_LEAD_HOURS before the appointment
    reminder_at = (datetime.fromisoformat(start_time) - timedelta(hours=REMINDER_LEAD_HOURS)).isoformat()
    reminder = create_reminder(patient_id, appointment_id, "appointment", reminder_at)

    log_audit_event(
        actor_id=state["user_id"],
        action="scheduled_reminder",
        entity_type="reminder",
        entity_id=reminder["id"],
        metadata={"scheduled_at": reminder_at},
        workflow_run_id=workflow_run_id,
    )
    update_workflow_run(
        workflow_run_id,
        current_step="followup",
        state={"reminder_id": reminder["id"]},
        status="completed",
    )

    confirmation = AIMessage(
        content="I've scheduled a reminder to be emailed to you a day before your appointment."
    )
    return {"messages": [confirmation], "delegated_to": None}
