from pydantic import BaseModel


class CreatePatientRequest(BaseModel):
    date_of_birth: str
    phone: str
    preferred_language: str
    emergency_contact: str