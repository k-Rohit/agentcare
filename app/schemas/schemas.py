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
