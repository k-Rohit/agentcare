from postgrest.exceptions import APIError

from app.services.supabase.factory import get_supabase_client

PATIENT_FACING_APPOINTMENT_FIELDS = (
    "id, status, reason, doctors(name, department_id), "
    "appointment_slots(start_time, end_time)"
)


def list_active_doctor_ids(department_id: str) -> list[str]:
    response = (
        get_supabase_client()
        .table("doctors")
        .select("id")
        .eq("department_id", department_id)
        .eq("active", True)
        .execute()
    )
    return [doctor["id"] for doctor in response.data or []]


def list_available_slots_for_doctors(doctor_ids: list[str]) -> list[dict]:
    if not doctor_ids:
        return []
    response = (
        get_supabase_client()
        .table("appointment_slots")
        .select("*")
        .in_("doctor_id", doctor_ids)
        .eq("status", "available")
        .execute()
    )
    return response.data or []


def create_appointment(patient_id: str, doctor_id: str, slot_id: str, reason: str) -> dict:
    try:
        response = (
            get_supabase_client()
            .table("appointments")
            .insert({
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "slot_id": slot_id,
                "reason": reason,
                "status": "confirmed",
            })
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to book slot {slot_id}: {e}") from e
    return response.data[0]


def update_slot_status(slot_id: str, status: str) -> None:
    get_supabase_client().table("appointment_slots").update({"status": status}).eq("id", slot_id).execute()


def get_appointment_patient_view(appointment_id: str) -> dict | None:
    try:
        response = (
            get_supabase_client()
            .table("appointments")
            .select(PATIENT_FACING_APPOINTMENT_FIELDS)
            .eq("id", appointment_id)
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to fetch appointment details for {appointment_id}: {e}") from e
    return response.data[0] if response.data else None


def list_patient_appointments(patient_id: str) -> list[dict]:
    try:
        response = (
            get_supabase_client()
            .table("appointments")
            .select(PATIENT_FACING_APPOINTMENT_FIELDS)
            .eq("patient_id", patient_id)
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to fetch appointments for patient {patient_id}: {e}") from e
    return response.data or []


def list_overlapping_slots(doctor_id: str, start_time: str, end_time: str) -> list[dict]:
    try:
        response = (
            get_supabase_client()
            .table("appointment_slots")
            .select("id")
            .eq("doctor_id", doctor_id)
            .neq("status", "cancelled")
            .lt("start_time", end_time)
            .gt("end_time", start_time)
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to check for overlapping slots for doctor {doctor_id}: {e}") from e
    return response.data or []


def create_slot(doctor_id: str, start_time: str, end_time: str) -> dict:
    try:
        response = (
            get_supabase_client()
            .table("appointment_slots")
            .insert({"doctor_id": doctor_id, "start_time": start_time, "end_time": end_time})
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to create appointment slot for doctor {doctor_id}: {e}") from e
    return response.data[0]


def get_appointment_slot_id(appointment_id: str) -> str | None:
    try:
        response = (
            get_supabase_client()
            .table("appointments")
            .select("id, slot_id")
            .eq("id", appointment_id)
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to look up appointment {appointment_id}: {e}") from e
    return response.data[0]["slot_id"] if response.data else None


def update_appointment_status(appointment_id: str, status: str) -> dict:
    try:
        response = (
            get_supabase_client()
            .table("appointments")
            .update({"status": status})
            .eq("id", appointment_id)
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to update appointment {appointment_id}: {e}") from e
    return response.data[0]


def get_slot_for_reschedule(slot_id: str) -> dict | None:
    try:
        response = (
            get_supabase_client()
            .table("appointment_slots")
            .select("id, doctor_id, status")
            .eq("id", slot_id)
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to look up slot {slot_id}: {e}") from e
    return response.data[0] if response.data else None


def update_appointment_slot(appointment_id: str, slot_id: str, doctor_id: str, status: str) -> dict:
    try:
        response = (
            get_supabase_client()
            .table("appointments")
            .update({"slot_id": slot_id, "doctor_id": doctor_id, "status": status})
            .eq("id", appointment_id)
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to reschedule appointment {appointment_id}: {e}") from e
    return response.data[0]

