from pydantic import BaseModel

class SubmitRequest(BaseModel):
    message: str | None = None           # absent when resuming (send resume_value instead)
    conversation_id: str | None = None   # absent on a fresh conversation
    resume_value: str | None = None      # set when answering an interrupt (e.g. chosen slot_id)
    resume_label: str | None = None      # human-readable version of the choice, to save in the transcript
    document_path: str | None = None
    document_filename: str | None = None
    
