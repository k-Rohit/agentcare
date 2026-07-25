# This file is used to create the route for the staff and doctors registration and login. 
# It will handle the requests and responses for the staff and doctors registration and login.

from fastapi import APIRouter, Depends
from app.schemas.staff import CreateDoctorRequest, CreateStaffRequest, ResolveEscalationRequest
from app.services.supabase.auth_ops import create_auth_account
from app.services.supabase.factory import get_supabase_client
from app.tools.audit import log_audit_event
from app.tools.escalations import get_pending_escalations, resolve_escalation
from auth import require_role
import logging  

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/register-doctor")
def create_doctor(request: CreateDoctorRequest, current_user: dict = Depends(require_role("admin"))):
    """Admin-only: provision a doctor's auth account, promote the profile to role=doctor, and create the doctors row."""
    logger.info(f"Admin {current_user['id']} creating doctor account for {request.email}")
    client = get_supabase_client()
    new_user_id, temp_password = create_auth_account(request.email, request.name)
    logger.info(f"Auth account created for {request.email} (user_id={new_user_id})")

    client.table("profiles").update({"role": "doctor"}).eq("id", new_user_id).execute()
    logger.info(f"Promoted profile {new_user_id} to role=doctor")

    client.table("doctors").insert({
        "user_id": new_user_id,
        "department_id": request.department_id,
        "name": request.name,
        "active": True,
    }).execute()
    logger.info(f"Doctor row created for user {new_user_id} in department {request.department_id}")

    client.table("audit_events").insert({
        "actor_id": current_user["id"],
        "action": "created_doctor",
        "entity_type": "doctor",
        "entity_id": new_user_id,
        "metadata": {"email": request.email, "department_id": request.department_id},
    }).execute()
    logger.info(f"Audit event recorded for doctor creation: {new_user_id}")

    return {"user_id": new_user_id, "temporary_password": temp_password}


@router.post("/register-staff")
def create_staff(request: CreateStaffRequest, current_user: dict = Depends(require_role("admin"))):
    """
    Admin-only: provision a staff's auth account, promote the profile to role=staff, and create the staff row.
    """
    logger.info(f"Admin {current_user['id']} creating staff account for {request.email}")
    client = get_supabase_client()
    new_user_id, temp_password = create_auth_account(request.email, request.name)
    logger.info(f"Auth account created for {request.email} (user_id={new_user_id})")

    client.table("profiles").update({"role": "staff"}).eq("id", new_user_id).execute()
    logger.info(f"Promoted profile {new_user_id} to role=staff")

    client.table("staff").insert({
        "user_id": new_user_id,
        "department_id": request.department_id,
        "name": request.name,
        "job_title": request.job_title,
        "employee_id": request.employee_id,
        "active": True,
    }).execute()
    logger.info(f"Staff row created for user {new_user_id} in department {request.department_id}")

    client.table("audit_events").insert({
        "actor_id": current_user["id"],
        "action": "created_staff",
        "entity_type": "staff",
        "entity_id": new_user_id,
        "metadata": {"email": request.email, "department_id": request.department_id},
    }).execute()
    logger.info(f"Audit event recorded for staff creation: {new_user_id}")

    return {"user_id": new_user_id, "temporary_password": temp_password}

@router.get("/escalations")
def list_escalations(current_user: dict = Depends(require_role("admin"))):
    return get_pending_escalations()

@router.post("/escalations/{escalation_id}/resolve")
def resolve(escalation_id: str,
            request: ResolveEscalationRequest,
            current_user: dict = Depends(require_role("staff", "admin"))):
    """Record a staff member's decision on an escalation."""
    
    log_audit_event(actor_id=current_user["id"], action=f"escalation_{request.status}",
                    entity_type="escalation", entity_id=escalation_id)
    
    return resolve_escalation(
        escalation_id=escalation_id,
        reviewed_by=current_user["id"],
        status=request.status,
    )