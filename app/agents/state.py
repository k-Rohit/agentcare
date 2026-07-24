from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

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
    messages: Annotated[list[BaseMessage], add_messages]
    delegated_to: str | None
    """Which node should run next, e.g. "routing", "appointment", "document",
    "followup", "escalate". Set by whichever node just finished deciding what
    happens next; None once the workflow is complete."""
    slot_choice: str | None
    """The slot_id the patient picked, passed back in to resume a paused
    Appointment run; None on a fresh request."""
    document_path: str | None
