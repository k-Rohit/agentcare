from app.services.supabase.factory import get_supabase_client
import logging

logger = logging.getLogger(__name__)

def get_available_slots(department_id: str) -> list[dict | None]:
    """List open appointment slots for doctors in a given department.

    Use this after a request has been routed to a department, to see what
    times are actually bookable before offering any to the patient or calling
    book_appointment. Only slots with status="available" are returned —
    never offer a slot that isn't in this list, since it may already be
    booked or belong to an inactive doctor.

    Args:
        department_id: The department's id (from get_departments or
            get_department_by_name), not its name.

    Returns:
        A list of appointment_slots rows, each shaped like:
        {"id": "<uuid>", "doctor_id": "<uuid>", "start_time": "...",
         "end_time": "...", "status": "available"}
        Returns an empty list if the department has no doctors, or no
        doctor in it currently has an open slot.
    """
    # get every active doctor_id in the department first
    client = get_supabase_client()
    response = client.table("doctors") \
                .select("id") \
                .eq("department_id", department_id) \
                .eq("active", True) \
                .execute()
    if response.data:
        doctor_ids = [doctor["id"] for doctor in response.data]
    else:
        logger.warning(f"No active doctors found for department {department_id}")
        return []

    # now using all doctor_ids, get the available slots from any of them
    response = client.table("appointment_slots") \
                .select("*") \
                .in_("doctor_id", doctor_ids) \
                .eq("status", "available") \
                .execute()
    if response.data:
        return response.data
    else:
        logger.info(f"No available slots found for department {department_id}")
        return []
    