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
