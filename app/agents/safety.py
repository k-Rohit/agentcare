from langchain_openai import ChatOpenAI

from app.agents.prompts import SAFETY_AGENT_PROMPT
from app.agents.state import WorkflowState
from app.schemas.schemas import SafetyAllow, SafetyBlock
from app.tools.departments import get_departments
from app.tools.escalations import create_escalation
from app.tools.workflow import update_workflow_run
from config import get_settings

def safety_node(state: WorkflowState) -> dict:
    workflow_run_id = state["workflow_run_id"]
    
    def escalate_request(reason: str) -> dict:
        """Escalate this request for human review, because no department in
    the list confidently fits, or the request sounds like it may
    describe a medical emergency."""
        return create_escalation(workflow_run_id=workflow_run_id, reason=reason)  
    
    settings = get_settings()
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.openai_api_key)
    llm_with_tools = llm.bind_tools([escalate_request, SafetyAllow, SafetyBlock])
    
    response = llm_with_tools.invoke([
        ('system', SAFETY_AGENT_PROMPT),
        ('human',state['raw_request'])
    ]) 
    
    if not response.tool_calls:
        raise RuntimeError("Safety Agent did not call a tool")
    
    call = response.too_calls[0]
    
    if call["name"] == "escalate_request":
        escalate_request(**call["args"])
        update_workflow_run(
        workflow_run_id,
        current_step="routing",
        state={"escalated": True, "reason": call["args"]["reason"]},
        status="escalated")
        return 
    {
        "escalation_reason": call["args"]["reason"],
        "status": "escalated",
        "delegated_to": None
    }
    
    if call["name"] == "SafetyAllow":
        update_workflow_run(
            workflow_run_id,
            current_step="safety",
            state={"escalated": False, "reason": call["args"]["reason"]},
            status="in progress"
        )
    if call["name"] == "SafetyBlock":
        update_workflow_run(
            workflow_run_id,
            current_step="safety",
            state={"escalated": False, "reason": call["args"]["reason"]},
            status="blocked"
        )