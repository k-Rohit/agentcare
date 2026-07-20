from postgrest.exceptions import APIError

from app.services.supabase.factory import get_supabase_client


def get_departments() -> list[dict]:
    """List every currently active hospital department.

    Use this to see the full set of valid departments before deciding which
    one a patient's request belongs to. Only pick from names that actually
    appear in this list — never invent a department name that isn't here,
    and never route to a department that isn't active.

    Args:
        None.

    Returns:
        A list of dicts, each shaped like:
        {"id": "<uuid>", "name": "Cardiology", "description": "Heart and cardiovascular care"}
        Returns an empty list if no departments are currently active.
    """
    client = get_supabase_client()
    try:
        response = (
            client.table("departments")
            .select("id, name, description")
            .eq("active", True)
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to fetch departments: {e}") from e
    return response.data


def get_department_by_name(name: str) -> dict | None:
    """Look up one active department's full record, including its id, by name.

    Use this after you've already decided which department a request belongs
    to (e.g. from get_departments), to get the real department_id needed for
    further steps like finding doctors in that department. Matching is
    case-insensitive, so "cardiology" and "Cardiology" both match the same row.

    Args:
        name: The department name to look up, e.g. "Cardiology". Should be a
            name that appeared in the list returned by get_departments.

    Returns:
        A dict shaped like {"id": "<uuid>", "name": "Cardiology", "description": "..."}
        if an active department with that name exists, otherwise None.
    """
    client = get_supabase_client()
    try:
        response = (
            client.table("departments")
            .select("id, name, description")
            .eq("active", True)
            .ilike("name", name)
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to look up department '{name}': {e}") from e
    return response.data[0] if response.data else None