from langgraph.graph import START, END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.appointment import appointment_agent_node, appointment_finalize_node, tools
from app.agents.coordinator import coordinator_node
from app.agents.checkpointer import setup_checkpointer
from app.agents.document import document_node
from app.agents.followup import followup_node
from app.agents.routing import routing_node
from app.agents.safety import safety_node
from app.agents.state import WorkflowState


def route_delegation(state: WorkflowState) -> str:
    """Convert the state's high-level delegation into a graph node name.

    Most nodes only need to set delegated_to/status. Keeping the branching here
    prevents a web of conditional edges as the workflow grows.
    """
    if state.get("status") in {"blocked", "escalated", "completed"}:
        return END

    delegated_to = state.get("delegated_to")
    if delegated_to == "routing":
        return "router_node"
    if delegated_to == "appointment":
        return "appointment_agent_node"
    if delegated_to == "document":
        return "document_node"
    if delegated_to == "followup":
        return "followup_node"

    return END

checkpointer = setup_checkpointer()
graph = StateGraph(WorkflowState)

# add the nodes
graph.add_node("coordinator_node", coordinator_node)
graph.add_node("safety_node", safety_node)
graph.add_node("router_node", routing_node)
graph.add_node("appointment_agent_node", appointment_agent_node)
graph.add_node("appointment_finalize_node", appointment_finalize_node)
graph.add_node("document_node", document_node)
graph.add_node("followup_node", followup_node)
graph.add_node("tools", ToolNode(tools))

graph.add_edge(START, "coordinator_node")
graph.add_edge("coordinator_node", "safety_node")

graph.add_conditional_edges(
    "safety_node",
    route_delegation,
    {
        "router_node": "router_node",
        "appointment_agent_node": "appointment_agent_node",
        "document_node": "document_node",
        "followup_node": "followup_node",
        END: END,
    },
)

graph.add_conditional_edges(
    "router_node",
    route_delegation,
    {
        "appointment_agent_node": "appointment_agent_node",
        "document_node": "document_node",
        "followup_node": "followup_node",
        END: END,
    },
)

graph.add_conditional_edges(
    "appointment_agent_node",
    tools_condition,
    {
        "tools": "tools",
        END: "appointment_finalize_node",
    },
)
graph.add_edge("tools", "appointment_agent_node")
graph.add_edge("appointment_finalize_node", "followup_node")
graph.add_edge("document_node", END)
graph.add_edge("followup_node", END)

workflow = graph.compile(checkpointer=checkpointer)
