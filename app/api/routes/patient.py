from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.tools.patients import get_or_create_patient_profile
from app.services.appointments import get_patient_appointments
from app.services.documents import get_documents, upload_document, get_document_url
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


@router.post("/documents/upload")
async def upload(file: UploadFile = File(...), patient_id: str = Depends(get_current_patient_id)):
    """Upload a file's bytes to the private bucket and return its storage path.

    The browser can't write to the private bucket (it only holds the publishable
    key), so the upload goes through here with the service-role key. The path is
    then sent to /chat as document_path, which triggers the Document Agent.
    """
    content = await file.read()
    # namespace with a short random prefix so re-uploading the same filename
    # doesn't collide in storage; keep the original name for classification.
    stored_name = f"{uuid4().hex[:8]}_{file.filename}"
    path = upload_document(patient_id, stored_name, content)
    return {"path": path, "filename": file.filename}


@router.get("/documents/{document_id}/url")
def document_url(document_id: str, patient_id: str = Depends(get_current_patient_id)):
    """A temporary signed URL to view one of the patient's own documents."""
    rows = (
        get_supabase_client()
        .table("patient_documents")
        .select("file_path")
        .eq("id", document_id)
        .eq("patient_id", patient_id)  # ownership check
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"url": get_document_url(rows[0]["file_path"])}


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
