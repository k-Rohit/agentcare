import logging

from postgrest.exceptions import APIError

from app.services.supabase.factory import get_supabase_client

logger = logging.getLogger(__name__)


def create_workflow_run(patient_id: str, current_step: str, state: dict) -> dict:
    """Create a new workflow_runs row to track a patient's request through the agent pipeline.

    Use this once, in the Coordinator node, at the very start of handling a
    new request. Every later node should update this same row (via
    update_workflow_run) rather than creating a new one.

    Args:
        patient_id: The patient_profiles.id this request belongs to.
        current_step: The name of the node that just ran, e.g. "coordinator".
        state: Whatever this step wants persisted, e.g.
            {"intent_type": "booking", "summary": "..."}.

    Returns:
        The newly created workflow_runs row as a dict, with status="in_progress".

    Raises:
        RuntimeError: If the insert fails.
    """
    client = get_supabase_client()
    try:
        response = client.table("workflow_runs").insert({
            "patient_id": patient_id,
            "current_step": current_step,
            "state": state,
            "status": "in_progress",
        }).execute()
    except APIError as e:
        logger.error(f"Failed to create workflow_run for patient {patient_id}: {e}")
        raise RuntimeError(f"Failed to create workflow_run: {e}") from e
    return response.data[0]


def update_workflow_run(workflow_run_id: str, current_step: str, state: dict, status: str = "in_progress") -> dict:
    """Update an existing workflow_runs row's progress.

    Use this after every node runs (except the Coordinator, which creates
    the row instead) — this is what makes the workflow resumable rather than
    only ever living in memory.

    Args:
        workflow_run_id: The workflow_runs.id to update.
        current_step: The name of the node that just ran, e.g. "routing".
        state: The full current state to persist — this REPLACES the stored
            state entirely, it does not merge with what was there before.
            Since LangGraph already accumulates every node's contributions
            into one in-memory state object as the graph runs, pass that
            whole object here, not just this node's own new fields, or
            earlier steps' data will be silently overwritten.
        status: One of "in_progress", "completed", "failed", "escalated".
            Defaults to "in_progress".

    Returns:
        The updated workflow_runs row as a dict.

    Raises:
        RuntimeError: If the update fails, or no workflow_run with that id exists.
    """
    client = get_supabase_client()
    try:
        response = (
            client.table("workflow_runs")
            .update({"current_step": current_step, "state": state, "status": status})
            .eq("id", workflow_run_id)
            .execute()
        )
    except APIError as e:
        logger.error(f"Failed to update workflow_run {workflow_run_id}: {e}")
        raise RuntimeError(f"Failed to update workflow_run: {e}") from e
    if not response.data:
        raise RuntimeError(f"No workflow_run found with id {workflow_run_id}")
    return response.data[0]
