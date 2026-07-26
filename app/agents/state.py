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
    """The storage path of a file the patient attached this turn (uploaded to the
    private bucket by the /documents/upload endpoint). Its presence is what
    triggers the Document Agent."""
    document_filename: str | None
    """The original filename of the attached document, used to classify its type."""
    history: list[dict]
    """The recent clean transcript of THIS conversation ({role, content}), loaded
    from the chat_messages table at the start of each turn and fed to the agents
    as short-term memory. Distinct from `messages`, which is per-turn ReAct
    scratch (system prompts, tool calls) that gets reset each message."""
    routing_note: str | None
    """The routing agent's warm, patient-facing line naming the chosen department,
    shown just before the slot picker. Set only when routing runs this turn;
    reset each turn by the coordinator."""
    attach_hint: bool
    """True when the patient also asked to attach a document alongside their main
    request; used to nudge them toward the paperclip button once the task is done."""
