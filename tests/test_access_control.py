"""Access-control (IDOR) and response-shape checks.

The test patient (random UUID) owns nothing, so any resource scoped to another
owner must come back 404, and its own listings must be empty lists — never a
leak of someone else's data.
"""
import uuid

from tests.conftest import API


def test_conversations_list_is_empty_for_new_patient(client):
    r = client.get(f"{API}/conversations")
    assert r.status_code == 200
    assert r.json() == []


def test_cannot_read_a_conversation_it_does_not_own(client):
    r = client.get(f"{API}/conversations/{uuid.uuid4()}/messages")
    assert r.status_code == 404


def test_cannot_delete_a_conversation_it_does_not_own(client):
    r = client.delete(f"{API}/conversations/{uuid.uuid4()}")
    assert r.status_code == 404


def test_cannot_get_url_for_a_document_it_does_not_own(client):
    r = client.get(f"{API}/documents/{uuid.uuid4()}/url")
    assert r.status_code == 404


def test_appointments_returns_a_list(client):
    r = client.get(f"{API}/appointments")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_documents_returns_a_list(client):
    r = client.get(f"{API}/documents")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_reminders_returns_a_list(client):
    r = client.get(f"{API}/reminders")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
