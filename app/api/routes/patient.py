from fastapi import APIRouter, Depends

from app.tools.patients import get_or_create_patient_profile
from app.tools.appointments import get_patient_appointments
from app.tools.documents import get_documents
from app.tools.reminders import get_patient_reminders
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

