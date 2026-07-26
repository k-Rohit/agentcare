from typing import Literal

from pydantic import BaseModel


class CoordinatorDecision(BaseModel):
    """The Coordinator's single decision about a patient message — it is also the
    safety gate, so this one call decides everything: route to a specialist,
    reply directly, or escalate an emergency."""
    action: Literal["book", "manage", "document", "reply", "escalate"]
    summary: str
    """A one-sentence, purely administrative summary (used as the conversation title)."""
    reply: str = ""
    """What to say to the patient - filled for "reply" (greeting/thanks/small talk,
    or a polite decline of a medical-advice request) and "escalate" (a calm
    message telling them to seek urgent help). Ignored for the task actions."""
    attach_hint: bool = False
    """True when the patient ALSO mentions wanting to attach/upload/share a
    document or report alongside their main request (e.g. "book cardiology and
    attach my ECG"). Lets us nudge them to use the paperclip button after the
    main task, without derailing into a separate document flow."""


class RoutingDecision(BaseModel):
    """The routing agent's confident choice of department. Used as an LLM tool —
    the model calls this when it's sure which department fits. Escalation is a
    separate tool (create_escalation), not a field here."""
    routed_department: str
    summary: str
    patient_message: str
    """A warm, natural one-sentence message to show the patient — it names the
    department and hints that available times are coming next. Friendly and
    administrative only; never diagnoses, interprets symptoms, or gives advice."""


class AppointmentResponse(BaseModel):
    """The response from the appointment agent with the details of the appointment."""
    appointment_id: str
    slot_id: str


class ClassifyDocument(BaseModel):
    """The document agent's classification of an uploaded document."""
    classification: Literal[
        "lab_report", "ecg", "imaging", "prescription", "discharge_summary", "referral", "other"
    ]
    summary: str