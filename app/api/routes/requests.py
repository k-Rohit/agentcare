from uuid import uuid4
from app.schemas.requests import SubmitRequest
from fastapi import APIRouter, Depends
from auth import get_current_user
from app.agents.graph import agentcare
from langchain_core.messages import AIMessage

requests = APIRouter()
from fastapi import APIRouter, Depends, HTTPException

@requests.post("/chat")
def chat(request: SubmitRequest, current_user: dict = Depends(get_current_user)):
    # RESUME — answering a paused interrupt (e.g. the patient picked a slot)
    if request.resume_value is not None:
        if not request.conversation_id:
            raise HTTPException(400, "conversation_id is required to resume")
        result = agentcare.resume(request.resume_value, request.conversation_id)
        return _to_response(request.conversation_id, result)

    if not request.message:
        raise HTTPException(400, "message is required")
    
    conversation_id = request.conversation_id or str(uuid4())
    state = {
        "user_id": current_user["id"],
        "patient_id": None,
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
    return _to_response(conversation_id, result)   # <-- you were missing this return

def _to_response(conversation_id, result):
    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        return {"conversation_id": conversation_id, "status": "awaiting_input",
    "reply": None, "interrupt": payload}

    status = result.get("status")
    if status == "blocked":
        return {"conversation_id": conversation_id, "status": "blocked",
    "reply": "I can't help with that — it's asking for medical advice.", "interrupt": None}
    if status == "escalated":
        return {"conversation_id": conversation_id, "status": "escalated",
    "reply": "This has been escalated to a staff member for review.", "interrupt": None}

    return {"conversation_id": conversation_id, "status": "completed",
    "reply": _last_reply(result.get("messages", [])), "interrupt": None}


def _last_reply(messages):
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content and not m.tool_calls:
            return m.content
        return None

        
        
        
        
    
    

