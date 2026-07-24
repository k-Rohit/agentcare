from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from app.agents.state import WorkflowState
from app.tools.documents import store_document
from app.tools.audit import log_audit_event
from app.tools.workflow import update_workflow_run
from app.agents.prompts import DOCUMENT_AGENT_PROMPT
from app.schemas.schemas import ClassifyDocument
from config import get_settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

settings = get_settings()
llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)
structured_llm = llm.with_structured_output(ClassifyDocument)

def document_node(state: WorkflowState):
    """
    This node is responsible for handling the uploads of the document.
    """
    workflow_run_id = state.get('workflow_run_id',None)
    document_path = state.get('document_path',None)
    patient_id = state['patient_id']
    if not document_path:
        raise RuntimeError("No document found to upload")
    
    # classify the document type
    response: ClassifyDocument = structured_llm.invoke([
    SystemMessage(content=DOCUMENT_AGENT_PROMPT),
    HumanMessage(content=f"Classify this document.\nFilename: {state['document_filename']}"),]) # type: ignore

    document_type = response.classification
    summary = response.summary
    
    try:
        stored = store_document(patient_id, document_type, document_path, datetime.now().date().isoformat())
    except Exception as e:
        logger.error(f"Failed to store document for patient {patient_id}: {e}")
        raise RuntimeError(f"Failed to store document for patient {patient_id}: {e}")

    log_audit_event(
        actor_id=state["user_id"],
        action="uploaded_document",
        entity_type="document",
        entity_id=stored["id"],
        metadata={"document_type": document_type, "summary": summary},
        workflow_run_id=workflow_run_id,
    )
    update_workflow_run(
        workflow_run_id,
        current_step="document",
        state={"document_id": stored["id"], "document_type": document_type},
    )

    confirmation = AIMessage(content=f"I've filed your {document_type.replace('_', ' ')} under your record.")
    return {"messages": [confirmation], "delegated_to": None}
    

    
    
    
    
    