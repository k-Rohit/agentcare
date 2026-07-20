from pydantic import BaseModel

class CreateDoctorRequest(BaseModel):
    email: str
    name: str
    department_id: str
