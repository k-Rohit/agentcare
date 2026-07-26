from app.services.appointments import (
    book_appointment as _book_appointment,
    cancel_appointment as _cancel_appointment,
    get_appointment_details as _get_appointment_details,
    get_available_slots as _get_available_slots,
    get_patient_appointments as _get_patient_appointments,
    reschedule_appointment as _reschedule_appointment,
)


def get_available_slots(department_id: str) -> list[dict]:
    """List open appointment slots for doctors in a given department."""
    return _get_available_slots(department_id)


def book_appointment(patient_id: str, slot_id: str, department_id: str, reason: str) -> dict:
    """Book a specific open slot for a patient."""
    return _book_appointment(patient_id, slot_id, department_id, reason)


def get_appointment_details(appointment_id: str) -> dict | None:
    """Get a patient-facing view of an appointment, with doctor and slot time."""
    return _get_appointment_details(appointment_id)


def get_patient_appointments(patient_id: str) -> list[dict]:
    """List every appointment a patient has, with doctor name and actual time."""
    return _get_patient_appointments(patient_id)


def reschedule_appointment(appointment_id: str, new_slot_id: str) -> dict:
    """Move an existing appointment to a different open slot."""
    return _reschedule_appointment(appointment_id, new_slot_id)


def cancel_appointment(appointment_id: str) -> dict:
    """Cancel an existing appointment and free its slot for others."""
    return _cancel_appointment(appointment_id)

