from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import AuthApiError

from app.services.supabase.factory import get_supabase_client

bearer_scheme = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    token = credentials.credentials
    client = get_supabase_client()

    try:
        user_response = client.auth.get_user(token)
    except AuthApiError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        ) from e

    profile = (
        client.table("profiles")
        .select("id, role, name, email")
        .eq("id", user_response.user.id)
        .single()
        .execute()
    )

    if not profile.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No profile found for this account",
        )

    return profile.data


def require_role(*allowed_roles: str):
    def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized for this action",
            )
        return current_user

    return dependency
