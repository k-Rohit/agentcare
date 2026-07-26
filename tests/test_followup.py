"""Follow-up node: reminders only for upcoming appointments.

Regression test for the bug where cancelling an appointment still scheduled a
reminder (because appointment_id was set on the cancelled appointment).
"""
from unittest.mock import patch

from app.agents import followup


def _state(appointment_id="appt-1"):
    return {
        "appointment_id": appointment_id,
        "workflow_run_id": "wf-1",
        "patient_id": "patient-1",
        "user_id": "user-1",
    }


def test_no_reminder_for_cancelled_appointment():
    details = {"status": "cancelled", "appointment_slots": {"start_time": "2026-08-01T10:00:00"}}
    with patch.object(followup, "get_appointment_details", return_value=details), \
         patch.object(followup, "create_reminder") as create_reminder:
        result = followup.followup_node(_state())
    create_reminder.assert_not_called()   # the bug: this used to be called
    assert result == {}


def test_no_reminder_for_completed_appointment():
    details = {"status": "completed", "appointment_slots": {"start_time": "2026-08-01T10:00:00"}}
    with patch.object(followup, "get_appointment_details", return_value=details), \
         patch.object(followup, "create_reminder") as create_reminder:
        result = followup.followup_node(_state())
    create_reminder.assert_not_called()
    assert result == {}


def test_reminder_scheduled_for_confirmed_appointment():
    details = {"status": "confirmed", "appointment_slots": {"start_time": "2026-08-01T10:00:00"}}
    with patch.object(followup, "get_appointment_details", return_value=details), \
         patch.object(followup, "create_reminder", return_value={"id": "reminder-1"}) as create_reminder, \
         patch.object(followup, "log_audit_event"), \
         patch.object(followup, "update_workflow_run"):
        result = followup.followup_node(_state())
    create_reminder.assert_called_once()
    assert "messages" in result


def test_reminder_scheduled_for_rescheduled_appointment():
    details = {"status": "rescheduled", "appointment_slots": {"start_time": "2026-08-01T10:00:00"}}
    with patch.object(followup, "get_appointment_details", return_value=details), \
         patch.object(followup, "create_reminder", return_value={"id": "reminder-2"}) as create_reminder, \
         patch.object(followup, "log_audit_event"), \
         patch.object(followup, "update_workflow_run"):
        result = followup.followup_node(_state())
    create_reminder.assert_called_once()


def test_no_reminder_when_nothing_actionable():
    result = followup.followup_node(_state(appointment_id=None))
    assert result == {}
