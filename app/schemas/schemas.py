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
    intent_type: Literal["booking", "document", "status_check", "other"]
    summary: str

class RoutingDecision(BaseModel):
    """The routing agent's confident choice of department. Used as an LLM tool —
    the model calls this when it's sure which department fits. Escalation is a
    separate tool (create_escalation), not a field here."""
    routed_department: str
    summary: str