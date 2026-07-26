import logging

from app.repositories import appointments as appointment_repo
from app.tools.departments import get_department_name

logger = logging.getLogger(__name__)


def get_available_slots(department_id: str) -> list[dict]:
    """List the open appointment slots in a department.

    Call this before offering the patient any times. Returns a list of slots
    (each with id, start/end time, and doctor); an empty list means nothing is
    currently open in that department.
    """
    doctor_ids = appointment_repo.list_active_doctor_ids(department_id)
    if not doctor_ids:
        logger.warning(f"No active doctors found for department {department_id}")
        return []

    slots = appointment_repo.list_available_slots_for_doctors(doctor_ids)
    if not slots:
        logger.info(f"No available slots found for department {department_id}")
    return slots


def book_appointment(patient_id: str, slot_id: str, department_id: str, reason: str) -> dict:
    """Book a specific open slot for a patient.

    Only call with a slot_id returned by get_available_slots (and picked by the
    patient). `reason` is a short administrative note drawn from the request.
    Returns the created appointment record.
    """
    department_name = get_department_name(department_id)
    logger.info(
        f"Attempting to book appointment for patient {patient_id} "
        f"in department {department_name} for slot {slot_id}"
    )

    available_slots = get_available_slots(department_id)
    matching_slot = next((slot for slot in available_slots if slot["id"] == slot_id), None)
    if matching_slot is None:
        raise ValueError("The requested slot is not available for booking. Please choose a different slot.")

    appointment = appointment_repo.create_appointment(
        patient_id=patient_id,
        doctor_id=matching_slot["doctor_id"],
        slot_id=slot_id,
        reason=reason,
    )
    appointment_repo.update_slot_status(slot_id, "booked")

    logger.info(
        f"Successfully booked appointment for patient {patient_id} "
        f"in department {department_name} for slot {slot_id}"
    )
    return appointment


def get_appointment_details(appointment_id: str) -> dict | None:
    """Read back one appointment (doctor, time, status) to confirm its details
    from the persisted record rather than from memory."""
    return appointment_repo.get_appointment_patient_view(appointment_id)


def get_patient_appointments(patient_id: str) -> list[dict]:
    """List every appointment on file for a patient (doctor, time, status).

    Use this for a status check, or to find which appointment the patient means
    before rescheduling or cancelling.
    """
    return appointment_repo.list_patient_appointments(patient_id)


def create_appointment_slot(doctor_id: str, start_time: str, end_time: str) -> dict:
    """Create a new bookable slot for a doctor (a staff/admin action).

    Rejects a slot that overlaps an existing one for the same doctor.
    """
    overlapping = appointment_repo.list_overlapping_slots(doctor_id, start_time, end_time)
    if overlapping:
        raise ValueError(
            f"This slot overlaps with an existing slot for this doctor "
            f"({len(overlapping)} conflicting slot(s) found)."
        )
    return appointment_repo.create_slot(doctor_id, start_time, end_time)


def cancel_appointment(appointment_id: str) -> dict:
    """Cancel an appointment and free its slot. Confirm with the patient first."""
    slot_id = appointment_repo.get_appointment_slot_id(appointment_id)
    if slot_id is None:
        raise ValueError(f"No appointment found with id {appointment_id}.")

    appointment = appointment_repo.update_appointment_status(appointment_id, "cancelled")
    appointment_repo.update_slot_status(slot_id, "available")
    logger.info(f"Cancelled appointment {appointment_id} and freed slot {slot_id}")
    return appointment


def reschedule_appointment(appointment_id: str, new_slot_id: str) -> dict:
    """Move an existing appointment to a new open slot (same department).

    `new_slot_id` must come from get_available_slots. Frees the old slot and
    books the new one.
    """
    old_slot_id = appointment_repo.get_appointment_slot_id(appointment_id)
    if old_slot_id is None:
        raise ValueError(f"No appointment found with id {appointment_id}.")

    new_slot = appointment_repo.get_slot_for_reschedule(new_slot_id)
    if not new_slot or new_slot["status"] != "available":
        raise ValueError(f"Slot {new_slot_id} is not available to reschedule into.")

    appointment = appointment_repo.update_appointment_slot(
        appointment_id=appointment_id,
        slot_id=new_slot_id,
        doctor_id=new_slot["doctor_id"],
        status="rescheduled",
    )
    appointment_repo.update_slot_status(new_slot_id, "booked")
    appointment_repo.update_slot_status(old_slot_id, "available")

    logger.info(f"Rescheduled appointment {appointment_id} from slot {old_slot_id} to {new_slot_id}")
    return appointment
