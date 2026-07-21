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