from postgrest.exceptions import APIError

from app.services.supabase.factory import get_supabase_client
from app.tools.departments import get_department_name
import logging

logger = logging.getLogger(__name__)

# Shared select shape for any query that returns an appointment for display
# to a patient — includes the doctor's name and the slot's actual time,
# neither of which live on the raw appointments row.
PATIENT_FACING_APPOINTMENT_FIELDS = "id, status, reason, doctors(name, department_id), appointment_slots(start_time, end_time)"

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

def get_appointment_details(appointment_id: str) -> dict | None:
    """Get a patient-facing view of an appointment, with the doctor's name and actual time.

    Use this right after book_appointment succeeds, to build a confirmation
    message, or whenever showing a patient their appointment status. The raw
    appointments row only has ids (doctor_id, slot_id) — nothing a patient
    would recognize — so always use this instead of the raw row when
    displaying anything to a human.

    Args:
        appointment_id: The appointments.id to look up (e.g. from
            book_appointment's return value).

    Returns:
        A dict shaped like:
        {"id": "...", "status": "confirmed", "reason": "...",
         "doctors": {"name": "Dr. Sharma"},
         "appointment_slots": {"start_time": "...", "end_time": "..."}}
        or None if no appointment with that id exists.
    """
    client = get_supabase_client()
    try:
        response = (
            client.table("appointments")
            .select(PATIENT_FACING_APPOINTMENT_FIELDS)
            .eq("id", appointment_id)
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to fetch appointment details for {appointment_id}: {e}") from e
    return response.data[0] if response.data else None

def get_patient_appointments(patient_id: str) -> list[dict]:
    """List every appointment a patient has, with doctor name and actual time.

    Use this to show a patient their appointment history/status, or to check
    for existing appointments before booking a new one.

    Args:
        patient_id: The patient's id (patient_profiles.id, not user_id).

    Returns:
        A list of dicts, each shaped like:
        {"id": "...", "status": "confirmed", "reason": "...",
         "doctors": {"name": "Dr. Sharma"},
         "appointment_slots": {"start_time": "...", "end_time": "..."}}
        Empty list if the patient has no appointments at all.
    """
    client = get_supabase_client()
    try:
        response = (
            client.table("appointments")
            .select(PATIENT_FACING_APPOINTMENT_FIELDS)
            .eq("patient_id", patient_id)
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to fetch appointments for patient {patient_id}: {e}") from e
    return response.data

def create_appointment_slot(doctor_id: str, start_time: str, end_time: str) -> dict:
    """Add a new open slot to a doctor's calendar.

    Use this when a doctor or staff member is adding availability — this is
    a doctor/staff-facing action, not something a patient's request should
    ever trigger directly. Rejects the new slot if it overlaps any of this
    doctor's existing non-cancelled slots (a cancelled slot frees up that
    time again, so it doesn't block a new one from being created there).

    Args:
        doctor_id: The doctor this slot belongs to (doctors.id).
        start_time: ISO 8601 timestamp, e.g. "2026-08-01T10:00:00+00:00".
        end_time: ISO 8601 timestamp, must be strictly after start_time.

    Returns:
        The newly created appointment_slots row as a dict, with status="available".

    Raises:
        ValueError: If the new slot overlaps an existing available/booked
            slot for the same doctor.
        RuntimeError: If the insert fails for a database reason — e.g.
            end_time not after start_time, or doctor_id doesn't exist.
    """
    client = get_supabase_client()

    # Two ranges [start1, end1) and [start2, end2) overlap exactly when
    # start1 < end2 AND start2 < end1 — so find any existing slot for this
    # doctor where that holds against the new slot's own start/end.
    try:
        overlapping = (
            client.table("appointment_slots")
            .select("id")
            .eq("doctor_id", doctor_id)
            .neq("status", "cancelled")
            .lt("start_time", end_time)
            .gt("end_time", start_time)
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to check for overlapping slots for doctor {doctor_id}: {e}") from e

    if overlapping.data:
        raise ValueError(
            f"This slot overlaps with an existing slot for this doctor "
            f"({len(overlapping.data)} conflicting slot(s) found)."
        )

    try:
        response = client.table("appointment_slots").insert({
            "doctor_id": doctor_id,
            "start_time": start_time,
            "end_time": end_time,
        }).execute()
    except APIError as e:
        raise RuntimeError(f"Failed to create appointment slot for doctor {doctor_id}: {e}") from e
    return response.data[0]


def cancel_appointment(appointment_id: str) -> dict:
    """Cancel an existing appointment and free its slot for others.

    Marks the appointment as cancelled and releases its slot back to
    "available" so another patient can book that time.

    Args:
        appointment_id: The appointments.id to cancel.

    Returns:
        The updated (cancelled) appointments row as a dict.

    Raises:
        ValueError: If no appointment with that id exists.
        RuntimeError: If the update fails for a database reason.
    """
    client = get_supabase_client()

    try:
        existing = (
            client.table("appointments").select("id, slot_id").eq("id", appointment_id).execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to look up appointment {appointment_id}: {e}") from e
    if not existing.data:
        raise ValueError(f"No appointment found with id {appointment_id}.")

    slot_id = existing.data[0]["slot_id"]

    try:
        response = (
            client.table("appointments")
            .update({"status": "cancelled"})
            .eq("id", appointment_id)
            .execute()
        )
        # free the slot back up
        client.table("appointment_slots").update({"status": "available"}).eq("id", slot_id).execute()
    except APIError as e:
        raise RuntimeError(f"Failed to cancel appointment {appointment_id}: {e}") from e

    logger.info(f"Cancelled appointment {appointment_id} and freed slot {slot_id}")
    return response.data[0]


def reschedule_appointment(appointment_id: str, new_slot_id: str) -> dict:
    """Move an existing appointment to a different open slot.

    Frees the appointment's current slot, books the new one, and updates the
    appointment (including its doctor, since the new slot may belong to a
    different doctor). The new slot must currently be available.

    Args:
        appointment_id: The appointments.id to reschedule.
        new_slot_id: The id of an available slot to move the appointment to
            (from get_available_slots).

    Returns:
        The updated appointments row as a dict, with status "rescheduled".

    Raises:
        ValueError: If the appointment doesn't exist, or the new slot isn't
            currently available.
        RuntimeError: If the update fails for a database reason.
    """
    client = get_supabase_client()

    try:
        existing = (
            client.table("appointments").select("id, slot_id").eq("id", appointment_id).execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to look up appointment {appointment_id}: {e}") from e
    if not existing.data:
        raise ValueError(f"No appointment found with id {appointment_id}.")
    old_slot_id = existing.data[0]["slot_id"]

    # the new slot must exist and be available
    try:
        new_slot = (
            client.table("appointment_slots")
            .select("id, doctor_id, status")
            .eq("id", new_slot_id)
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to look up slot {new_slot_id}: {e}") from e
    if not new_slot.data or new_slot.data[0]["status"] != "available":
        raise ValueError(f"Slot {new_slot_id} is not available to reschedule into.")

    new_doctor_id = new_slot.data[0]["doctor_id"]

    try:
        response = (
            client.table("appointments")
            .update({
                "slot_id": new_slot_id,
                "doctor_id": new_doctor_id,
                "status": "rescheduled",
            })
            .eq("id", appointment_id)
            .execute()
        )
        # book the new slot, free the old one
        client.table("appointment_slots").update({"status": "booked"}).eq("id", new_slot_id).execute()
        client.table("appointment_slots").update({"status": "available"}).eq("id", old_slot_id).execute()
    except APIError as e:
        raise RuntimeError(f"Failed to reschedule appointment {appointment_id}: {e}") from e

    logger.info(f"Rescheduled appointment {appointment_id} from slot {old_slot_id} to {new_slot_id}")
    return response.data[0]
