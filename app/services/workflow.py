import logging

from app.repositories.workflow import (
    get_workflow_run,
    get_workflow_state,
    insert_workflow_run,
    update_workflow_run_row,
)

logger = logging.getLogger(__name__)


def get_or_create_workflow_run(workflow_run_id: str, patient_id: str, current_step: str = "coordinator") -> dict:
    existing = get_workflow_run(workflow_run_id)
    if existing:
        return existing
    return insert_workflow_run(workflow_run_id, patient_id, current_step)


def update_workflow_run(workflow_run_id: str, current_step: str, state: dict, status: str | None = "in_progress") -> dict:
    current_state = get_workflow_state(workflow_run_id)
    merged_state = {**(current_state or {}), **state}
    payload = {"current_step": current_step, "state": merged_state}
    if status is not None:
        payload["status"] = status
    return update_workflow_run_row(workflow_run_id, payload)
