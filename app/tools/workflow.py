from app.services.workflow import (
    get_or_create_workflow_run as _get_or_create_workflow_run,
    update_workflow_run as _update_workflow_run,
)


def get_or_create_workflow_run(workflow_run_id: str, patient_id: str, current_step: str = "coordinator") -> dict:
    """Compatibility wrapper; workflow persistence is implemented in services."""
    return _get_or_create_workflow_run(workflow_run_id, patient_id, current_step)


def update_workflow_run(workflow_run_id: str, current_step: str, state: dict, status: str | None = "in_progress") -> dict:
    """Compatibility wrapper; workflow persistence is implemented in services."""
    return _update_workflow_run(workflow_run_id, current_step, state, status)
