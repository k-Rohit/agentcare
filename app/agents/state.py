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
