"""Shared pytest fixtures.

The API tests use FastAPI's TestClient with the auth dependencies overridden, so
they exercise route logic (validation, ownership checks, response shapes) without
needing a real Supabase JWT. The overridden patient id is a random UUID that owns
nothing, which is exactly what we want for the access-control tests: any lookup
scoped to it comes back empty / 404.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from auth import get_current_user
from app.api.routes.patient import get_current_patient_id

API = "/agentcare/api/v1"

# A synthetic user/patient that owns no data — perfect for validation and
# access-control tests (never collides with real rows).
TEST_USER_ID = str(uuid.uuid4())
TEST_PATIENT_ID = str(uuid.uuid4())


def _fake_user() -> dict:
    return {"id": TEST_USER_ID, "role": "patient", "name": "Test Patient", "email": "test@example.com"}


@pytest.fixture
def client():
    """An authenticated client: auth + patient-id resolution are stubbed."""
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_current_patient_id] = lambda: TEST_PATIENT_ID
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def anon_client():
    """A client with no auth override — used to assert endpoints are protected."""
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c
