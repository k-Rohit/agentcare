from langchain_openai import ChatOpenAI

from config import get_settings
from app.agents.prompts import COORDINATOR_SYSTEM_PROMPT
from app.agents.state import WorkflowState
from app.schemas.schemas import RequestIntent
from app.tools.audit import log_audit_event
from app.tools.patients import get_or_create_patient_profile
from app.tools.workflow import get_or_create_workflow_run, update_workflow_run

# Where the Coordinator sends each classified intent next. "other" goes to
# escalate rather than guessing, since nothing downstream is built to
# confidently handle an unclassified administrative request yet.
INTENT_TO_NEXT_NODE = {
    "new_booking": "routing",          # a NEW appointment needs a department first
    "manage_appointment": "appointment",  # reschedule / cancel / status of an existing one
    "document": "document",
    "other": "escalate",
}


def coordinator_node(state: WorkflowState) -> dict:
    """Entry point of the workflow.

    Resolves the patient's identity (creating a bare patient_profiles row on
    a first-time request), classifies the high-level intent of their raw
    request with its own LLM call, and creates the workflow_runs row that
    the rest of the graph will persist its progress into.
    """
    patient_profile = get_or_create_patient_profile(state["user_id"])
    workflow_run_id = state["workflow_run_id"]  # the conversation id, from the frontend

    settings = get_settings()
    llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)
    structured_llm = llm.with_structured_output(RequestIntent)

    intent = structured_llm.invoke([
        ("system", COORDINATOR_SYSTEM_PROMPT),
        ("human", state["raw_request"]),
    ])

    # Create the conversation's workflow_run once (first message), reuse after.
    get_or_create_workflow_run(workflow_run_id, patient_profile["id"])
    update_workflow_run(
        workflow_run_id,
        current_step="coordinator",
        state={"intent_type": intent.intent_type, "summary": intent.summary},
    )

    delegated_to = INTENT_TO_NEXT_NODE[intent.intent_type]

    # Append this step to the audit trail, under the conversation's workflow id.
    log_audit_event(
        actor_id=state["user_id"],  # profiles.id (what audit_events.actor_id references)
        action="classified_intent",
        entity_type="workflow_run",
        entity_id=workflow_run_id,
        metadata={"intent_type": intent.intent_type, "delegated_to": delegated_to},
        workflow_run_id=workflow_run_id,
    )

    return {
        "patient_id": patient_profile["id"],
        "workflow_run_id": workflow_run_id,
        "delegated_to": delegated_to,
    }
