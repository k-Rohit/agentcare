from langgraph.graph import START, END, StateGraph
from langgraph.prebuilt import ToolNode,tools_condition

from app.agents.appointment import appointment_agent_node, appointment_finalize_node
from app.agents.checkpointer import setup_checkpointer
from app.agents.coordinator import coordinator_node
from app.agents.document import document_node
from app.agents.followup import followup_node
from app.agents.routing import routing_node
from app.agents.safety import safety_node
from app.agents.state import WorkflowState
from app.tools.appointments import book_appointment, cancel_appointment, reschedule_appointment, get_appointment_details,get_patient_appointments

# define the tools - 
tools = [book_appointment, cancel_appointment, reschedule_appointment, get_appointment_details,get_patient_appointments]

# define the checkpointer
checkpointer = setup_checkpointer()

graph = StateGraph(WorkflowState)

# add the nodes
graph.add_node('coordinator_node', coordinator_node)
graph.add_node('safety_node', safety_node)
graph.add_node('router_node', routing_node)
graph.add_node('appointment_agent_node', appointment_agent_node)
graph.add_node('appointment_finalize_node', appointment_finalize_node)
graph.add_node('document_node',document_node)
graph.add_node('followup_node', followup_node)
graph.add_node('tools', ToolNode(tools))



