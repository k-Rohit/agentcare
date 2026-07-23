import logging

from postgrest.exceptions import APIError

from app.services.supabase.factory import get_supabase_client

logger = logging.getLogger(__name__)


def log_audit_event(
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    metadata: dict | None = None,
    workflow_run_id: str | None = None,
) -> dict:
    """Record one action in the permanent audit trail.

    Use this after any state-changing action (booking, cancelling, creating
    an account, resolving an escalation, etc.) — every real change in the
    system should leave a trace here. Never pass a password or other secret
    in metadata; this table is permanent and never cleaned up.

    Args:
        actor_id: The profiles.id of who performed the action, or None if
            the system itself did it (e.g. an automated follow-up).
        action: A short, consistent label for what happened, e.g.
            "created_doctor", "booked_appointment", "resolved_escalation".
        entity_type: What kind of thing this action was about, e.g.
            "doctor", "appointment", "escalation". Not a foreign key —
            just a plain label used together with entity_id.
        entity_id: The id of the specific row this action affected.
        metadata: Any extra context worth keeping, e.g. {"email": "..."}.
            Defaults to an empty dict if not given.
        workflow_run_id: The conversation/workflow this step belongs to, so
            all steps of one workflow can be pulled together. None for audit
            events not tied to a workflow (e.g. an admin creating a doctor).

    Returns:
        The newly created audit_events row as a dict.

    Raises:
        RuntimeError: If the insert fails.
    """
    client = get_supabase_client()
    try:
        response = client.table("audit_events").insert({
            "actor_id": actor_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metadata": metadata or {},
            "workflow_run_id": workflow_run_id,
        }).execute()
    except APIError as e:
        logger.error(f"Failed to log audit event '{action}' for {entity_type} {entity_id}: {e}")
        raise RuntimeError(f"Failed to log audit event: {e}") from e
    return response.data[0]
