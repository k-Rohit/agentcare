from typing import Literal

from pydantic import BaseModel


class RequestIntent(BaseModel):
    """The Coordinator's classification of a request's high-level intent."""
    intent_type: Literal["new_booking", "manage_appointment", "document", "other"]
    summary: str


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


class SafetyAllow(BaseModel):
    """Allow the request to proceed as normal administrative handling."""
    reason: str


class SafetyBlock(BaseModel):
    """Block the request because it asks the system for medical advice/diagnosis/dosage."""
    reason: str


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