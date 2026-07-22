from typing import TypedDict


class WorkflowState(TypedDict):
    user_id: str
    patient_id: str | None
    workflow_run_id: str | None
    raw_request: str
    department: str | None
    department_id: str | None
    slot_id: str | None
    appointment_id: str | None
    escalation_reason: str | None
    status: str
    delegated_to: str | None
    """Which node should run next, e.g. "routing", "appointment", "document",
    "followup", "escalate". Set by whichever node just finished deciding what
    happens next; None once the workflow is complete."""
    pending_options: list | None
    """Slot options surfaced to the patient when the Appointment agent pauses
    for a selection; None when not waiting on a choice."""
    slot_choice: str | None
    """The slot_id the patient picked, passed back in to resume a paused
    Appointment run; None on a fresh request."""
