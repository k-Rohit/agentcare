from app.utils import create_temporary_password
from app.services.supabase.factory import get_supabase_client
from supabase import AuthApiError
from fastapi import HTTPException


def create_auth_account(email: str, name: str) -> tuple[str, str]:
    client = get_supabase_client()
    temp_password = create_temporary_password()
    try:
        result = client.auth.admin.create_user({
            "email": email,
            "password": temp_password,
            "email_confirm": True,
            "user_metadata": {"full_name": name},
        })
    except AuthApiError as e:
        raise HTTPException(status_code=409, detail=f"Could not create account: {e}") from e
    return result.user.id, temp_password
