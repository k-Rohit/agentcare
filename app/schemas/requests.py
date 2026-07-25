from pydantic import BaseModel

class SubmitRequest(BaseModel):
    message: str
    conversation_id: str
    document_path: str | None = None
    resume_value: str | None = None
    document_filename: str | None = None
    
