from langchain_core.messages import AIMessage, RemoveMessage

from app.services.llm import get_chat_model
from app.agents.prompts import COORDINATOR_SYSTEM_PROMPT
from app.agents.state import WorkflowState
from app.schemas.agents import CoordinatorDecision
from app.tools.audit import log_audit_event
from app.tools.escalations import create_escalation
from app.tools.patients import get_or_create_patient_profile
from app.services.workflow import get_or_create_workflow_run, update_workflow_run

# The three task actions hand off to a specialist node. "reply" and "escalate"
# are handled by the coordinator itself and end the turn.
ACTION_TO_NEXT_NODE = {"book": "routing", "manage": "appointment", "document": "document"}


def _turn(patient_id: str, workflow_run_id: str, **decision) -> dict:
    """Coordinator's return for one message: clear last turn's routing flags (a
    conversation reuses one thread, so they would otherwise leak in), then layer
    this turn's decision on top. `messages` (memory) is cleared separately, by id.
    """
    return {
        "patient_id": patient_id, "workflow_run_id": workflow_run_id,
        "department": None, "department_id": None, "slot_id": None, "slot_choice": None,
        "appointment_id": None, "escalation_reason": None, "status": None,
        "delegated_to": None, "routing_note": None, "attach_hint": False,
        **decision,
    }


def coordinator_node(state: WorkflowState) -> dict:
    """The single front door AND safety gate. One LLM call decides whether to
    escalate an emergency, reply directly (chit-chat or a medical-advice decline),
    or hand a real task to a specialist. An attached file skips the LLM and goes
    straight to the Document Agent.
    """
    patient = get_or_create_patient_profile(state["user_id"])
    run_id = state["workflow_run_id"]
    get_or_create_workflow_run(run_id, patient["id"])

    # clear last turn's ReAct scratch messages (durable memory lives in `history`)
    clear = [RemoveMessage(id=m.id) for m in state.get("messages", []) if getattr(m, "id", None)]

    def record(action: str, summary: str, status: str = "in_progress"):
        update_workflow_run(run_id, current_step="coordinator",
                            state={"action": action, "summary": summary}, status=status)
        log_audit_event(actor_id=state["user_id"], action=action, entity_type="workflow_run",
                        entity_id=run_id, metadata={"summary": summary}, workflow_run_id=run_id)

    # A file was attached → unambiguously a document task; skip the classifier.
    if state.get("document_path"):
        record("document", f"Patient attached a document: {state.get('document_filename')}")
        return _turn(patient["id"], run_id, delegated_to="document", messages=clear)

    # Classify (this is also the safety gate) in one call, with recent history so
    # follow-ups like "yes sure" resolve against what was just discussed.
    llm = get_chat_model()
    history_msgs = [("assistant" if h["role"] == "assistant" else "human", h["content"])
                    for h in (state.get("history") or [])]
    decision = llm.with_structured_output(CoordinatorDecision).invoke(
        [("system", COORDINATOR_SYSTEM_PROMPT), *history_msgs, ("human", state["raw_request"])]
    )

    # Emergency → flag for staff and stop.
    if decision.action == "escalate":
        create_escalation(workflow_run_id=run_id, reason=decision.summary)
        record("escalate", decision.summary, status="escalated")
        return _turn(patient["id"], run_id, status="escalated", escalation_reason=decision.summary,
                     messages=clear + [AIMessage(content=decision.reply)])

    # Not a task (greeting / thanks / medical-advice decline) → reply directly.
    if decision.action == "reply":
        record("reply", decision.summary, status="completed")
        return _turn(patient["id"], run_id, status="completed",
                     messages=clear + [AIMessage(content=decision.reply)])

    # A real task → hand off to the specialist. Carry the attach hint so we can
    # nudge the patient toward the paperclip once the task is done.
    record(decision.action, decision.summary)
    return _turn(patient["id"], run_id, delegated_to=ACTION_TO_NEXT_NODE[decision.action],
                 attach_hint=decision.attach_hint, messages=clear)
