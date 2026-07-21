from postgrest.exceptions import APIError

from app.services.supabase.factory import get_supabase_client
from app.tools.departments import get_department_name
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

def book_appointment(patient_id: str, slot_id: str, department_id: str, reason: str) -> dict:
    """Book a specific open slot for a patient.

    Use this once a specific slot_id (from get_available_slots) has been
    chosen for the patient. The doctor is derived from the slot itself, not
    chosen separately — every slot belongs to exactly one doctor, so there's
    no independent doctor choice to make here.

    Args:
        patient_id: The patient's id (patient_profiles.id, not user_id).
        slot_id: The id of the specific slot being booked, must be one of
            the slots currently returned by get_available_slots for this
            department.
        department_id: The department the slot belongs to.
        reason: The reason for the appointment, stored on the appointments row.

    Returns:
        The newly created appointments row as a dict.

    Raises:
        ValueError: If slot_id isn't currently in the department's open slots.
        RuntimeError: If the booking fails for a database reason, e.g. someone
            else booked the exact same slot moments earlier.
    """
    department_name = get_department_name(department_id)
    logger.info(f"Attempting to book appointment for patient {patient_id} in department {department_name} for slot {slot_id}")

    available_slots = get_available_slots(department_id)
    matching_slot = next((slot for slot in available_slots if slot["id"] == slot_id), None)
    if matching_slot is None:
        raise ValueError("The requested slot is not available for booking. Please choose a different slot.")

    doctor_id = matching_slot["doctor_id"]
    client = get_supabase_client()

    try:
        response = client.table("appointments").insert({
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "slot_id": slot_id,
            "reason": reason,
            "status": "confirmed",
        }).execute()
    except APIError as e:
        raise RuntimeError(f"Failed to book slot {slot_id}: {e}") from e

    # mark the slot as taken so it stops appearing available to others
    client.table("appointment_slots").update({"status": "booked"}).eq("id", slot_id).execute()

    logger.info(f"Successfully booked appointment for patient {patient_id} in department {department_name} for slot {slot_id}")
    return response.data[0]
