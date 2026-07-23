from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
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

# define the llm to be used
settings = get_settings()
llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)

def select_appointment_slot(options: list[dict]) -> str:
    """
    This tool is used to get the desired appointment slot 
    from the user
    """
    selected_slot = interrupt({"type":"slot_selection", "options": options})
    return selected_slot

# define the tools that can be used by the llm
tools = [get_available_slots, book_appointment,
        get_appointment_details, get_patient_appointments,
        reschedule_appointment,cancel_appointment,
        select_appointment_slot]

# bind the llm with the tools
llm_with_tools = llm.bind_tools(tools=tools)

# Define the agent node (the think step) - 
def appointment_agent_node(state: WorkflowState) -> dict:
    messages = state['messages']
    if not messages: #first time entering appointment
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