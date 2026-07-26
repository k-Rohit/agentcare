from postgrest.exceptions import APIError

from app.services.supabase.factory import get_supabase_client


def get_workflow_run(workflow_run_id: str) -> dict | None:
    try:
        response = get_supabase_client().table("workflow_runs").select("*").eq("id", workflow_run_id).execute()
    except APIError as e:
        raise RuntimeError(f"Failed to fetch workflow_run {workflow_run_id}: {e}") from e
    return response.data[0] if response.data else None


def insert_workflow_run(workflow_run_id: str, patient_id: str, current_step: str) -> dict:
    try:
        response = (
            get_supabase_client()
            .table("workflow_runs")
            .insert({
                "id": workflow_run_id,
                "patient_id": patient_id,
                "current_step": current_step,
                "state": {},
                "status": "in_progress",
            })
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to create workflow_run {workflow_run_id}: {e}") from e
    return response.data[0]


def get_workflow_state(workflow_run_id: str) -> dict:
    try:
        response = get_supabase_client().table("workflow_runs").select("state").eq("id", workflow_run_id).execute()
    except APIError as e:
        raise RuntimeError(f"Failed to fetch workflow_run state {workflow_run_id}: {e}") from e
    return response.data[0]["state"] if response.data else {}


def update_workflow_run_row(workflow_run_id: str, payload: dict) -> dict:
    try:
        response = get_supabase_client().table("workflow_runs").update(payload).eq("id", workflow_run_id).execute()
    except APIError as e:
        raise RuntimeError(f"Failed to update workflow_run {workflow_run_id}: {e}") from e
    if not response.data:
        raise RuntimeError(f"No workflow_run found with id {workflow_run_id}")
    return response.data[0]
