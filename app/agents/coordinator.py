from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from config import get_settings
from app.agents.prompts import COORDINATOR_SYSTEM_PROMPT, CHAT_AGENT_PROMPT
from app.agents.state import WorkflowState
from app.schemas.agents import RequestIntent
from app.tools.audit import log_audit_event
from app.tools.patients import get_or_create_patient_profile
from app.tools.workflow import get_or_create_workflow_run, update_workflow_run

# Where the Coordinator sends each classified intent next. "chat" is handled by
# the Coordinator itself (a natural reply), so it isn't in this map.
INTENT_TO_NEXT_NODE = {
    "new_booking": "routing",          # a NEW appointment needs a department first
    "manage_appointment": "appointment",  # reschedule / cancel / status of an existing one
    "document": "document",
    "other": "escalate",
}


def coordinator_node(state: WorkflowState) -> dict:
    """Entry point of the workflow.

    Resolves the patient's identity, classifies the request's intent, and creates
    the conversation's workflow_run. Conversational messages ("hi", "thanks",
    "what can you do") are answered here directly with a friendly reply; task
    requests are delegated to the specialist nodes.
    """
    patient_profile = get_or_create_patient_profile(state["user_id"])
    workflow_run_id = state["workflow_run_id"]

    settings = get_settings()
    llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)

    intent = llm.with_structured_output(RequestIntent).invoke([
        ("system", COORDINATOR_SYSTEM_PROMPT),
        ("human", state["raw_request"]),
    ])

    get_or_create_workflow_run(workflow_run_id, patient_profile["id"])

    # Conversational (non-task) message → reply naturally, right here. No pipeline.
    if intent.intent_type == "chat":
        reply = llm.invoke([
            SystemMessage(content=CHAT_AGENT_PROMPT),
            HumanMessage(content=state["raw_request"]),
        ])
        update_workflow_run(
            workflow_run_id,
            current_step="chat",
            state={"intent_type": "chat", "summary": intent.summary, "reply": reply.content},
            status="completed",
        )
        log_audit_event(
            actor_id=state["user_id"],
            action="chat_reply",
            entity_type="workflow_run",
            entity_id=workflow_run_id,
            workflow_run_id=workflow_run_id,
        )
        return {
            "patient_id": patient_profile["id"],
            "workflow_run_id": workflow_run_id,
            "delegated_to": None,
            "status": "completed",        # graph ends after the coordinator for chat
            "messages": [AIMessage(content=reply.content)],
        }

    # Task request → record classification and delegate to a specialist.
    update_workflow_run(
        workflow_run_id,
        current_step="coordinator",
        state={"intent_type": intent.intent_type, "summary": intent.summary},
    )
    delegated_to = INTENT_TO_NEXT_NODE[intent.intent_type]
    log_audit_event(
        actor_id=state["user_id"],
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
