from uuid import uuid4
from app.schemas.requests import SubmitRequest
from fastapi import APIRouter, Depends
from auth import get_current_user
from app.agents.graph import agentcare
from langchain_core.messages import AIMessage

requests = APIRouter()
@requests.post("/chat")
def chat(request: SubmitRequest, current_user: dict = Depends(get_current_user)):
    conversation_id = request.conversation_id or str(uuid4())
    
    # define the initial state - 
    state = {
    "user_id": current_user["id"],
    "patient_id": None,
    # conversation id = workflow id = thread id
    "workflow_run_id": conversation_id,   
    "raw_request": request.message,
    "department": None, "department_id": None,
    "slot_id": None, "appointment_id": None,
    "escalation_reason": None, "status": "in_progress",
    "messages": [], "delegated_to": None, "slot_choice": None,
    "document_path": request.document_path,
    "document_filename": request.document_filename,
}
    result = agentcare.invoke(state=state, thread_id=conversation_id)


def _to_response(conversation_id, result):
    # a) paused for input (slot selection)
    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value # {"type": "slot_selection", "options": [...]}
        
        
    
    

