import logging

from postgrest.exceptions import APIError

from app.services.supabase.factory import get_supabase_client

logger = logging.getLogger(__name__)


def create_escalation(workflow_run_id: str, reason: str) -> dict:
    """Open a human-review record for a workflow that needs a person to step in.

    Use this whenever the Safety Agent flags an emergency/unsafe request, or
    the Routing Agent can't confidently map a request to any department —
    anything the system shouldn't try to resolve autonomously. The workflow
    this belongs to should stop making automated progress once this exists,
    until a staff member resolves it.

    Args:
        workflow_run_id: The workflow_runs.id this concern is about.
        reason: A plain-language explanation of why this needs human review.

    Returns:
        The newly created escalations row as a dict, with status="pending".

    Raises:
        RuntimeError: If the insert fails, e.g. workflow_run_id doesn't exist.
    """
    client = get_supabase_client()
    try:
        response = client.table("escalations").insert({
            "workflow_run_id": workflow_run_id,
            "reason": reason,
        }).execute()
    except APIError as e:
        logger.error(f"Failed to create escalation for workflow_run {workflow_run_id}: {e}")
        raise RuntimeError(f"Failed to create escalation: {e}") from e
    return response.data[0]


def get_pending_escalations() -> list[dict]:
    """List every escalation currently awaiting human review.

    Use this to populate a staff/admin dashboard of open concerns that need
    someone's attention.

    Returns:
        A list of escalations rows with status="pending". Empty list if
        nothing is currently awaiting review.
    """
    client = get_supabase_client()
    try:
        response = client.table("escalations").select("*").eq("status", "pending").execute()
    except APIError as e:
        logger.error(f"Failed to fetch pending escalations: {e}")
        raise RuntimeError(f"Failed to fetch pending escalations: {e}") from e
    return response.data


def resolve_escalation(escalation_id: str, reviewed_by: str, status: str) -> dict:
    """Record a staff member's decision on an escalation.

    Use this once a staff/admin has actually looked at a pending escalation
    and decided what to do with it — never call this automatically, it's
    meant to represent a real human decision.

    Args:
        escalation_id: The escalations.id being resolved.
        reviewed_by: The profiles.id of the staff/admin who reviewed it.
        status: One of "reviewed", "resolved", "rejected".

    Returns:
        The updated escalations row as a dict.

    Raises:
        RuntimeError: If the update fails, or no escalation with that id exists.
    """
    client = get_supabase_client()
    try:
        response = (
            client.table("escalations")
            .update({"reviewed_by": reviewed_by, "status": status})
            .eq("id", escalation_id)
            .execute()
        )
    except APIError as e:
        logger.error(f"Failed to resolve escalation {escalation_id}: {e}")
        raise RuntimeError(f"Failed to resolve escalation: {e}") from e
    if not response.data:
        raise RuntimeError(f"No escalation found with id {escalation_id}")
    return response.data[0]
