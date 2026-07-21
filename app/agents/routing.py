from langchain_openai import ChatOpenAI

from app.agents.prompts import ROUTING_AGENT_PROMPT
from app.agents.state import WorkflowState
from app.schemas.schemas import RoutingDecision
from app.tools.departments import get_departments
from app.tools.escalations import create_escalation
from app.tools.workflow import update_workflow_run
from config import get_settings


def routing_node(state: WorkflowState) -> dict:
    """Maps the patient's request to a real, active department.

    Fetches the current department list deterministically first (always
    needed, regardless of the specific request), then lets the LLM itself
    decide which of two tools applies: RoutingDecision if it's confident
    which department fits, or the real create_escalation tool if it isn't.
    The model chooses which function to invoke — Python doesn't decide that
    after the fact from a fixed structured output.
    """
    departments = get_departments()
    department_list_text = "\n".join(f"- {d['name']}: {d['description']}" for d in departments)

    workflow_run_id = state["workflow_run_id"]

    def escalate_request(reason: str) -> dict:
        """Escalate this request for human review, because no department in
        the list confidently fits, or the request sounds like it may
        describe a medical emergency."""
        return create_escalation(workflow_run_id=workflow_run_id, reason=reason)

    settings = get_settings()
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.openai_api_key)
    llm_with_tools = llm.bind_tools([escalate_request, RoutingDecision])

    response = llm_with_tools.invoke([
        ("system", ROUTING_AGENT_PROMPT),
        ("human", f"Available departments:\n{department_list_text}\n\nPatient request: {state['raw_request']}"),
    ])

    if not response.tool_calls:
        raise RuntimeError("Routing Agent did not call a tool; expected either RoutingDecision or escalate_request")

    call = response.tool_calls[0]

    if call["name"] == "escalate_request":
        escalate_request(**call["args"])
        update_workflow_run(
            workflow_run_id,
            current_step="routing",
            state={"escalated": True, "reason": call["args"]["reason"]},
            status="escalated",
        )
        return {
            "escalation_reason": call["args"]["reason"],
            "status": "escalated",
            "delegated_to": None,
        }

    decision = RoutingDecision(**call["args"])
    update_workflow_run(
        workflow_run_id,
        current_step="routing",
        state={"department": decision.routed_department, "summary": decision.summary},
        status="in_progress",
    )
    return {
        "department": decision.routed_department,
        "delegated_to": "appointment",
    }
