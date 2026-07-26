"""Request-validation and authentication guards for the API."""
from tests.conftest import API


# ── authentication ──────────────────────────────────────────────────────────
def test_me_requires_auth(anon_client):
    """Protected endpoints reject requests with no bearer token."""
    r = anon_client.get(f"{API}/me")
    assert r.status_code in (401, 403)


def test_chat_requires_auth(anon_client):
    r = anon_client.post(f"{API}/chat", json={"message": "hi"})
    assert r.status_code in (401, 403)


def test_conversations_requires_auth(anon_client):
    r = anon_client.get(f"{API}/conversations")
    assert r.status_code in (401, 403)


# ── /chat request validation ────────────────────────────────────────────────
def test_chat_empty_body_is_rejected(client):
    """No message and no resume_value → 400 (nothing to act on)."""
    r = client.post(f"{API}/chat", json={})
    assert r.status_code == 400
    assert "message" in r.json()["detail"].lower()


def test_chat_blank_message_is_rejected(client):
    r = client.post(f"{API}/chat", json={"message": ""})
    assert r.status_code == 400


def test_resume_without_conversation_id_is_rejected(client):
    """Resuming an interrupt needs the conversation to resume into."""
    r = client.post(f"{API}/chat", json={"resume_value": "some-slot-id"})
    assert r.status_code == 400
    assert "conversation_id" in r.json()["detail"].lower()


def test_me_returns_current_user(client):
    """With auth stubbed, /me echoes the resolved user profile."""
    r = client.get(f"{API}/me")
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "patient"
    assert "email" in body
