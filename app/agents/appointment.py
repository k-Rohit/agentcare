import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langgraph.types import interrupt

from app.agents.prompts import APPOINTMENT_AGENT_PROMPT
from app.agents.state import WorkflowState
from app.tools.audit import log_audit_event
from app.tools.workflow import update_workflow_run
from app.tools.appointments import (
    get_available_slots,
    book_appointment,
    get_appointment_details,
    get_patient_appointments,
    reschedule_appointment,
    cancel_appointment,
)

from config import get_settings

# define the llm to be used
settings = get_settings()
llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)


def select_appointment_slot(options: list[dict]) -> str:
    """Show the patient the available slots and pause until they pick one.

    Call this AFTER get_available_slots, passing the open slots as a list of
    {"slot_id": ..., "start": ..., "end": ...}. It pauses the workflow until
    the patient chooses, then returns the chosen slot_id — pass that straight
    into book_appointment. Never list slots as plain text and ask; always use
    this tool so the choice is captured reliably.
    """
    selected_slot = interrupt({"type": "slot_selection", "options": options})
    return selected_slot


# define the tools that can be used by the llm
tools = [get_available_slots, book_appointment,
        get_appointment_details, get_patient_appointments,
        reschedule_appointment, cancel_appointment,
        select_appointment_slot]

# bind the llm with the tools
llm_with_tools = llm.bind_tools(tools=tools)


def _last_appointment_action(messages):
    """Look back through the conversation for the most recent booking/
       reschedule/cancel tool result, and return (action_name, result_dict).
    """
    for message in reversed(messages):
        if (
            isinstance(message, ToolMessage)
            and message.content is not None
            and message.name in ("book_appointment", "reschedule_appointment", "cancel_appointment")
        ):
            try:
                data = json.loads(message.content) if isinstance(message.content, str) else message.content
            except (json.JSONDecodeError, TypeError):
                data = None
            return message.name, data
    return None, None


def appointment_finalize_node(state: WorkflowState) -> dict:
    """Runs once, after the LLM loop finishes. Deterministically records what
       the agent did — the LLM never touches this.
    """
    workflow_run_id = state["workflow_run_id"]
    action, data = _last_appointment_action(state["messages"])
    appointment_id = data.get("id") if isinstance(data, dict) else None

    if action:  # a booking/reschedule/cancel actually happened this turn
        log_audit_event(
            actor_id=state["user_id"],
            action=action,
            entity_type="appointment",
            entity_id=appointment_id or workflow_run_id,
            workflow_run_id=workflow_run_id,
        )

    update_workflow_run(
        workflow_run_id,
        current_step="appointment",
        state={"appointment_id": appointment_id},
    )
    return {"appointment_id": appointment_id}

# Define the agent node (the think step) -
def appointment_agent_node(state: WorkflowState) -> dict:
    messages = state['messages']
    if not messages:  # first time entering appointment
        messages = [
            SystemMessage(content=APPOINTMENT_AGENT_PROMPT),
            HumanMessage(content=f"patient_id: {state['patient_id']}\n"
                                f"department_id: {state['department_id']}\n"
                                f"request: {state['raw_request']}")
        ]
        response = llm_with_tools.invoke(messages)
        return {"messages": messages + [response]}
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}