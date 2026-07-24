from typing import Literal

from pydantic import BaseModel

class CreateDoctorRequest(BaseModel):
    email: str
    name: str
    department_id: str

class CreateStaffRequest(BaseModel):
    email: str
    name: str
    job_title: str
    employee_id: str
    department_id: str | None = None

class CreatePatientRequest(BaseModel):
    date_of_birth: str
    phone: str
    preferred_language: str
    emergency_contact: str

class RequestIntent(BaseModel):
    intent_type: Literal["new_booking", "manage_appointment", "document", "other"]
    summary: str

class RoutingDecision(BaseModel):
    """The routing agent's confident choice of department. Used as an LLM tool —
    the model calls this when it's sure which department fits. Escalation is a
    separate tool (create_escalation), not a field here."""
    routed_department: str
    summary: str

class SafetyAllow(BaseModel):
    """ Allow the request to proceed as normal administrative handling."""
    reason: str


class SafetyBlock(BaseModel):
    """Block the request because it asks the system for medical advice/diagnosis/dosage."""
    reason: str
    
class AppointmentResponse(BaseModel):
    """ The response from the appointment agent with the details of the appointment """
    appointment_id: str
    slot_id: str
    
class ClassifyDocument(BaseModel):
    """ The response from the document agent with the classification of the document """
    classification: Literal["lab_report","ecg","imaging","prescription","discharge_summary","referral","other"]
    summary: str