from fastapi import APIRouter, Depends, HTTPException

from app.tools.patients import get_or_create_patient_profile
from app.tools.appointments import get_patient_appointments
from app.tools.documents import get_documents
from app.tools.reminders import get_patient_reminders
from app.tools.chat_messages import get_chat_messages
from app.services.supabase.factory import get_supabase_client

from auth import get_current_user

router = APIRouter()


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    """Return the logged-in user's profile (id, role, name, email).

    The frontend calls this right after login to learn the user's role (which
    lives in the DB, not the token) so it can show the right UI, and to confirm
    the token is still valid.
    """
    return current_user

def get_current_patient_id(current_user: dict = Depends(get_current_user)) -> str:
    return get_or_create_patient_profile(current_user["id"])["id"]


@router.get("/appointments")
def appointments(patient_id: str = Depends(get_current_patient_id)):
    """The logged-in patient's appointments (doctor name, time, status)."""
    return get_patient_appointments(patient_id)


@router.get("/documents")
def documents(patient_id: str = Depends(get_current_patient_id)):
    """The logged-in patient's uploaded documents."""
    return get_documents(patient_id)


@router.get("/reminders")
def reminders(patient_id: str = Depends(get_current_patient_id)):
    """The logged-in patient's reminders."""
    return get_patient_reminders(patient_id)


@router.get("/conversations")
def conversations(patient_id: str = Depends(get_current_patient_id)):
    """The logged-in patient's past conversations (for the history sidebar)."""
    return (
        get_supabase_client()
        .table("workflow_runs")
        .select("id, current_step, status, state, created_at")
        .eq("patient_id", patient_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )


def _assert_owns_conversation(conversation_id: str, patient_id: str) -> None:
    """Guard: a patient may only touch their own conversations (prevents IDOR)."""
    owns = (
        get_supabase_client()
        .table("workflow_runs")
        .select("id")
        .eq("id", conversation_id)
        .eq("patient_id", patient_id)
        .execute()
        .data
    )
    if not owns:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.get("/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id: str, patient_id: str = Depends(get_current_patient_id)):
    """The clean transcript of one conversation (for replaying it in the chat view)."""
    _assert_owns_conversation(conversation_id, patient_id)
    return get_chat_messages(conversation_id)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, patient_id: str = Depends(get_current_patient_id)):
    """Delete one of the logged-in patient's conversations (and its audit rows)."""
    _assert_owns_conversation(conversation_id, patient_id)
    client = get_supabase_client()
    client.table("audit_events").delete().eq("workflow_run_id", conversation_id).execute()
    client.table("escalations").delete().eq("workflow_run_id", conversation_id).execute()
    client.table("workflow_runs").delete().eq("id", conversation_id).execute()
    return {"deleted": conversation_id}

