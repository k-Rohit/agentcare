"""The AgentCare workflow graph.

Wires the individual agent nodes into one compiled StateGraph, so the whole
pipeline runs from a single entry point instead of being sequenced by hand.

Flow:
    START ─► coordinator ─► safety ─┬─ blocked/escalated ─► END
                                    ├─ booking  ─► routing ─┬─ escalated ─► END
                                    │                       └─► appointment ─► END
                                    └─ status   ─► appointment ─► END

A resume (the patient picked a slot) enters directly at `appointment` via the
conditional entry point, so Coordinator/Safety/Routing don't re-run.
"""

from langgraph.graph import StateGraph, START, END

from app.agents.state import WorkflowState
from app.agents.coordinator import coordinator_node
from app.agents.safety import safety_node
from app.agents.routing import routing_node
from app.agents.appointment import appointment_node


def entry_router(state: WorkflowState) -> str:
    # A run carrying a slot_choice is resuming a paused booking — go straight
    # to appointment; a fresh request starts at coordinator.
    if state.get("slot_choice"):
        return "appointment"
    return "coordinator"


def after_safety(state: WorkflowState) -> str:
    if state["status"] in ("blocked", "escalated"):
        return END
    delegated = state.get("delegated_to")
    if delegated == "routing":
        return "routing"
    if delegated == "appointment":
        return "appointment"
    # "document" / "escalate" / anything else isn't wired into the graph yet
    return END


def after_routing(state: WorkflowState) -> str:
    if state["status"] == "escalated":
        return END
    return "appointment"


builder = StateGraph(WorkflowState)
builder.add_node("coordinator", coordinator_node)
builder.add_node("safety", safety_node)
builder.add_node("routing", routing_node)
builder.add_node("appointment", appointment_node)

builder.add_conditional_edges(
    START, entry_router, {"coordinator": "coordinator", "appointment": "appointment"}
)
builder.add_edge("coordinator", "safety")
builder.add_conditional_edges(
    "safety", after_safety, {"routing": "routing", "appointment": "appointment", END: END}
)
builder.add_conditional_edges(
    "routing", after_routing, {"appointment": "appointment", END: END}
)
builder.add_edge("appointment", END)

agentcare_graph = builder.compile()