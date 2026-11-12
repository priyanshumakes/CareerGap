"""Regression tests: /ats/keywords now has the same per-IP rate limit
as the other endpoints (it was the only authenticated POST without
one, so a client could hammer it unthrottled).
"""

from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials
import pytest

import backend


client = TestClient(backend.app)


@pytest.fixture(autouse=True)
def authenticated_user():
    backend.limiter._storage.reset()

    backend.app.dependency_overrides[
        backend.get_current_user
    ] = lambda: {
        "sub": "rate-limit-test-user",
        "email": "ratelimit@example.com",
    }

    backend.app.dependency_overrides[
        backend.security
    ] = lambda: HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="test-access-token",
    )

    yield

    backend.limiter._storage.reset()
    backend.app.dependency_overrides.pop(
        backend.get_current_user,
        None,
    )
    backend.app.dependency_overrides.pop(
        backend.security,
        None,
    )


def _payload():
    return {
        "resume": "I know Python.",
        "job_description": "Required: Python FastAPI Docker.",
        "projects": [
            {"name": "Test API", "description": "A Python API project."}
        ],
    }


def test_ats_keywords_still_answers_normally():
    response = client.post("/ats/keywords", json=_payload())

    assert response.status_code == 200
    assert "keywords" in response.json()


def test_ats_keywords_is_rate_limited():
    statuses = [
        client.post("/ats/keywords", json=_payload()).status_code
        for _ in range(11)
    ]

    assert statuses[:10] == [200] * 10
    assert statuses[10] == 429
