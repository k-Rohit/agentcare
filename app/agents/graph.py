from langgraph.graph import START, END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command

from app.agents.appointment import appointment_agent_node, appointment_finalize_node, tools
from app.agents.coordinator import coordinator_node
from app.agents.checkpointer import get_checkpointer, setup_checkpointer
from app.agents.document import document_node
from app.agents.followup import followup_node
from app.agents.routing import routing_node
from app.agents.safety import safety_node
from app.agents.state import WorkflowState


class AgentCare:
    """The compiled AgentCare workflow.

    Built once at startup (the graph is a reusable machine); each request is run
    through it via invoke()/resume() with its own state and conversation thread.
    """

    def __init__(self):
        setup_checkpointer()               # ensure checkpoint tables exist (idempotent)
        self.checkpointer = get_checkpointer()
        self.workflow = self._build_graph()

    def _route_delegation(self, state: WorkflowState) -> str:
        """Turn the live state's delegation into the next node name.

        Reads the state LangGraph passes in at runtime (never a stored copy), so
        it sees each node's latest updates. Centralising the branching here keeps
        the edges simple as the workflow grows.
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

    def _build_graph(self):
        graph = StateGraph(WorkflowState)

        # nodes
        graph.add_node("coordinator_node", coordinator_node)
        graph.add_node("safety_node", safety_node)
        graph.add_node("router_node", routing_node)
        graph.add_node("appointment_agent_node", appointment_agent_node)
        graph.add_node("appointment_finalize_node", appointment_finalize_node)
        graph.add_node("document_node", document_node)
        graph.add_node("followup_node", followup_node)
        graph.add_node("tools", ToolNode(tools))

        # entry: coordinator -> safety
        graph.add_edge(START, "coordinator_node")
        graph.add_edge("coordinator_node", "safety_node")

        # after safety, branch on the coordinator's delegation (or stop if blocked/escalated)
        graph.add_conditional_edges(
            "safety_node",
            self._route_delegation,
            {
                "router_node": "router_node",
                "appointment_agent_node": "appointment_agent_node",
                "document_node": "document_node",
                "followup_node": "followup_node",
                END: END,
            },
        )

        # after routing, go on to appointment (or stop if it escalated)
        graph.add_conditional_edges(
            "router_node",
            self._route_delegation,
            {
                "appointment_agent_node": "appointment_agent_node",
                "document_node": "document_node",
                "followup_node": "followup_node",
                END: END,
            },
        )

        # appointment ReAct loop: agent <-> tools, then finalize
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

        # document and followup are terminal
        graph.add_edge("document_node", END)
        graph.add_edge("followup_node", END)

        return graph.compile(checkpointer=self.checkpointer)

    def invoke(self, state: dict, thread_id: str) -> dict:
        """Run a fresh request through the workflow for a conversation."""
        return self.workflow.invoke(
            state, config={"configurable": {"thread_id": thread_id}}
        )

    def resume(self, resume_value, thread_id: str) -> dict:
        """Resume a paused run (e.g. after the patient picked a slot)."""
        return self.workflow.invoke(
            Command(resume=resume_value),
            config={"configurable": {"thread_id": thread_id}},
        )


# Build once at import; endpoints import this instance.
agentcare = AgentCare()