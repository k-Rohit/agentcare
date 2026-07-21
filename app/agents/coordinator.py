from langchain_openai import ChatOpenAI

from config import get_settings
from app.agents.prompts import COORDINATOR_SYSTEM_PROMPT
from app.agents.state import WorkflowState
from app.schemas.schemas import RequestIntent
from app.tools.patients import get_or_create_patient_profile
from app.tools.workflow import create_workflow_run

# Where the Coordinator sends each classified intent next. "other" goes to
# escalate rather than guessing, since nothing downstream is built to
# confidently handle an unclassified administrative request yet.
INTENT_TO_NEXT_NODE = {
    "booking": "routing",
    "document": "document",
    "status_check": "appointment",
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

    settings = get_settings()
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.openai_api_key)
    structured_llm = llm.with_structured_output(RequestIntent)

    intent = structured_llm.invoke([
        ("system", COORDINATOR_SYSTEM_PROMPT),
        ("human", state["raw_request"]),
    ])

    workflow_run = create_workflow_run(
        patient_id=patient_profile["id"],
        current_step="coordinator",
        state={"intent_type": intent.intent_type, "summary": intent.summary},
    )

    return {
        "patient_id": patient_profile["id"],
        "workflow_run_id": workflow_run["id"],
        "delegated_to": INTENT_TO_NEXT_NODE[intent.intent_type],
    }
