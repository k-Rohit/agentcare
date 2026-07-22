import json

from typing import Annotated, TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, ToolMessage
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import interrupt, Command

from app.agents.checkpointer import get_checkpointer
from app.agents.prompts import APPOINTMENT_AGENT_PROMPT
from app.agents.state import WorkflowState
from app.tools.appointments import (
    get_available_slots,
    book_appointment,
    get_appointment_details,
    get_patient_appointments,
    reschedule_appointment,
    cancel_appointment,
)
from app.tools.workflow import update_workflow_run
from config import get_settings


def select_appointment_slot(options: list[dict]) -> str:
    """
    Present the available slots to the patient and pause for their choice.

    Call this AFTER get_available_slots, BY ITSELF (not alongside any other
    tool call), passing the open slots as a list of
    {"slot_id": ..., "start": ..., "end": ...}. It pauses the workflow until
    the patient chooses, then returns the chosen slot_id — pass that straight
    into book_appointment. Do not ask the patient to choose in plain text;
    always use this tool so their selection is captured reliably.
    """
    return interrupt({"type": "slot_selection", "options": options})

# --- Appointment agent as a ReAct subgraph (LLM ⇄ ToolNode loop) ------------
# The LLM decides which action the request needs (book / reschedule / cancel /
# status) and calls the tools itself; ToolNode executes them and loops results
# back until the agent stops calling tools. Fully agentic — Python never
# decides the action, the model does.

settings = get_settings()

# create_appointment_slot is deliberately NOT here — that's a doctor/staff
# availability tool, never something a patient-booking agent should call.
tools = [
    get_available_slots,
    book_appointment,
    get_appointment_details,
    get_patient_appointments,
    reschedule_appointment,
    cancel_appointment,
    select_appointment_slot,
]

llm_with_tools = ChatOpenAI(model="gpt-4o-mini", api_key=settings.openai_api_key).bind_tools(tools)


class AppointmentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def agent_llm(state: AppointmentState) -> dict:
    return {"messages": [llm_with_tools.invoke(state["messages"])]}


builder = StateGraph(AppointmentState)
builder.add_node("agent", agent_llm)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)  # tool asked for? → tools, else → END
builder.add_edge("tools", "agent")                       # loop results back
# Compiled with the checkpointer so the conversation persists across turns
# (the patient sees slot options in one turn, replies with their pick in the
# next) keyed by thread_id = workflow_run_id.
appointment_graph = builder.compile(checkpointer=get_checkpointer())


def _extract_appointment(messages: list[BaseMessage]) -> dict | None:
    """Pull the most recent booked/rescheduled appointment out of the tool
    results in the conversation, if any."""
    found = None
    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.name in ("book_appointment", "reschedule_appointment"):
            try:
                data = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                if isinstance(data, dict) and data.get("id"):
                    found = data
            except (json.JSONDecodeError, TypeError):
                continue
    return found


def appointment_node(state: WorkflowState) -> dict:
    """Run the Appointment agent for this request.

    Feeds the patient's request plus the ids it needs (patient_id,
    department_id) into the ReAct loop, which reasons about what to do and
    calls the appointment tools itself. Persists the run under
    thread_id = workflow_run_id so a multi-turn slot selection can resume.
    """
    workflow_run_id = state["workflow_run_id"]
    config = {"configurable": {"thread_id": workflow_run_id}}

    if state.get("slot_choice"):
        # Resuming a run that paused for slot selection — feed the patient's
        # chosen slot_id back in; interrupt() returns it and the agent books.
        result = appointment_graph.invoke(Command(resume=state["slot_choice"]), config)
    else:
        context = (
            f"patient_id: {state['patient_id']}\n"
            f"department_id: {state['department_id']}\n"
            f"Patient request: {state['raw_request']}"
        )
        result = appointment_graph.invoke(
            {"messages": [("system", APPOINTMENT_AGENT_PROMPT), ("human", context)]},
            config=config,
        )

    # The agent paused to let the patient pick a slot — surface the options and
    # wait; the next call (with slot_choice set) resumes from here.
    if "__interrupt__" in result:
        options = result["__interrupt__"][0].value.get("options", [])
        update_workflow_run(
            workflow_run_id,
            current_step="appointment",
            state={"awaiting": "slot_selection", "options": options},
            status="in_progress",
        )
        return {
            "pending_options": options,
            "delegated_to": "appointment",  # stay here until the patient chooses
        }

    final_reply = result["messages"][-1].content
    appointment = _extract_appointment(result["messages"])
    appointment_id = appointment["id"] if appointment else state.get("appointment_id")
    slot_id = appointment["slot_id"] if appointment else state.get("slot_id")

    update_workflow_run(
        workflow_run_id,
        current_step="appointment",
        state={"reply": final_reply, "appointment_id": appointment_id},
        status="in_progress",
    )

    return {
        "appointment_id": appointment_id,
        "slot_id": slot_id,
        "pending_options": None,
        "delegated_to": None,
    }