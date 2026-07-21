from postgrest.exceptions import APIError
from app.services.supabase.factory import get_supabase_client
import logging

logger = logging.getLogger(__name__)

def get_or_create_patient_profile(user_id: str) -> dict:
    """Look up a patient's profile by their login user_id, creating a bare one if it doesn't exist yet.

    Use this to resolve a logged-in patient's user_id into their patient_id
    (patient_profiles.id) before doing anything else in the workflow, since
    appointments, documents, and workflow_runs all reference patient_id, not
    user_id directly. If no profile exists yet, this creates a minimal one
    (date_of_birth, phone, preferred_language, and emergency_contact all left
    null) so the workflow can proceed immediately, rather than blocking on the
    patient filling in those details first.

    Args:
        user_id: The patient's login id (profiles.id / auth.users.id).

    Returns:
        The patient_profiles row as a dict, either the existing one or the
        newly created bare one. Always has at least "id" and "user_id" set.
    """
    client = get_supabase_client()

    try:
        logger.info(f"Looking up patient profile for user {user_id}")
        response = (
            client.table("patient_profiles")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to look up patient profile for user {user_id}: {e}") from e

    if response.data:
        return response.data[0]

    try:
        logger.info(f"No patient profile found for user {user_id}, creating a new one...")
        created = client.table("patient_profiles").insert({"user_id": user_id}).execute()
        return created.data[0]
    except APIError as e:
        raise RuntimeError(f"Failed to create patient profile for user {user_id}: {e}") from e
    
