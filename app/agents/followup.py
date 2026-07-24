from datetime import datetime, timedelta
import logging

from langchain_core.messages import AIMessage

from app.agents.state import WorkflowState
from app.tools.appointments import get_appointment_details
from app.tools.reminders import create_reminder
from app.tools.audit import log_audit_event
from app.tools.workflow import update_workflow_run

logger = logging.getLogger(__name__)

REMINDER_LEAD_HOURS = 24


def followup_node(state: WorkflowState) -> dict:
    """Schedule a reminder for a booked appointment (deterministic — no LLM).

    Runs after the appointment step. If an appointment was actually booked this
    turn, it creates a reminder row timed 24h before the appointment. It does
    NOT send an email — a separate reminder-sender process sends due reminders.
    If nothing was booked (status check, document-only request), it's a no-op.
    """
    appointment_id = state.get("appointment_id")
    workflow_run_id = state["workflow_run_id"]

    if not appointment_id:
        return {}  # nothing was booked this turn → no reminder to schedule

    details = get_appointment_details(appointment_id)
    if not details:
        logger.error(f"Follow-up: appointment {appointment_id} not found; skipping reminder")
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