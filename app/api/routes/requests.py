from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import AIMessage

from auth import get_current_user
from app.agents.graph import agentcare
from app.schemas.requests import SubmitRequest
from app.tools.chat_messages import add_chat_message, get_chat_messages

router = APIRouter()

# How many recent transcript lines to feed back as short-term memory.
HISTORY_LIMIT = 10

@router.post("/chat")
def chat(request: SubmitRequest, current_user: dict = Depends(get_current_user)):
    # RESUME — answering a paused interrupt (e.g. the patient picked a slot)
    if request.resume_value is not None:
        if not request.conversation_id:
            raise HTTPException(400, "conversation_id is required to resume")
        result = agentcare.resume(request.resume_value, request.conversation_id)
        response = _to_response(request.conversation_id, result)
        # Save the patient's choice (e.g. the picked slot) so it replays on reload.
        if request.resume_label:
            add_chat_message(request.conversation_id, "user", request.resume_label)
        if response["reply"]:
            add_chat_message(request.conversation_id, "assistant", response["reply"])
        return response

    if not request.message:
        raise HTTPException(400, "message is required")

    conversation_id = request.conversation_id or str(uuid4())
    # Short-term memory: the recent transcript of this conversation so far. Empty
    # for a brand-new conversation. Fed to the agents so they understand context
    # like "cancel the second one" or "the earlier appointment".
    history = get_chat_messages(conversation_id, limit=HISTORY_LIMIT) if request.conversation_id else []

    state = {
        "user_id": current_user["id"],
        "patient_id": None,
        "workflow_run_id": conversation_id,
        "raw_request": request.message,
        "history": history,
        "department": None, "department_id": None,
        "slot_id": None, "appointment_id": None,
        "escalation_reason": None, "status": "in_progress",
        "messages": [], "delegated_to": None, "slot_choice": None,
        "routing_note": None, "attach_hint": False,
        "document_path": request.document_path,
        "document_filename": request.document_filename,
    }
    result = agentcare.invoke(state=state, thread_id=conversation_id)
    response = _to_response(conversation_id, result)

    # Record this turn in the clean transcript (after invoke, so the workflow_run
    # the messages reference already exists). For a booking that pauses for slot
    # selection there's no reply yet — but there IS the routing announcement
    # ("let's find you an opening in …"), so save that instead.
    add_chat_message(conversation_id, "user", request.message)
    assistant_line = response.get("reply") or response.get("department_message")
    if assistant_line:
        add_chat_message(conversation_id, "assistant", assistant_line)
    return response

def _to_response(conversation_id, result):
    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        # Tell the patient which department we routed them to, before the slots.
        return {"conversation_id": conversation_id, "status": "awaiting_input",
                "reply": None, "interrupt": payload,
                "department": result.get("department"),
                "department_message": result.get("routing_note")}

    status = result.get("status")
    if status == "escalated":
        # The coordinator wrote the emergency reply itself (LLM), so show that.
        return {"conversation_id": conversation_id, "status": "escalated",
                "reply": _reply(result.get("messages", [])) or "This has been flagged for urgent staff attention.",
                "interrupt": None}

    reply = _reply(result.get("messages", []))
    # Multi-intent: the patient also asked to attach a document alongside the task.
    # We can't attach for them, so nudge them to the paperclip once it's done.
    if reply and result.get("attach_hint"):
        reply += ("\n\nYou can attach your documents (like your ECG or blood reports) "
                  "with the 📎 button, and I'll file them to your record.")
    return {"conversation_id": conversation_id, "status": "completed",
    "reply": reply, "interrupt": None}


def _reply(messages):
    """Join every assistant line produced this turn — so a booking shows BOTH the
    confirmation (doctor + time) AND the reminder note, not just the last one."""
    parts = [m.content for m in messages
             if isinstance(m, AIMessage) and m.content and not m.tool_calls]
    return "\n\n".join(parts) if parts else None # type: ignore
        
        
        
        
    
    

