"""Tests for the daily AI quota (ai_quota.py).

The quota protects the shared Groq free-plan allowance: a per-user
daily cap stops one account from draining it, and a global daily cap
stops many scripted accounts from draining it together. The suite
runs with effectively unlimited caps (see conftest.py); every test
here sets its own small caps and resets the counters.
"""

from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials
import pytest

import ai_quota
import backend


client = TestClient(backend.app)


@pytest.fixture(autouse=True)
def quota_state(monkeypatch):
    """Reset counters around each test and mock authentication."""
    ai_quota.reset_ai_quota()
    backend.limiter._storage.reset()

    backend.app.dependency_overrides[
        backend.get_current_user
    ] = lambda: {
        "sub": "quota-test-user",
        "email": "quota@example.com",
    }

    backend.app.dependency_overrides[
        backend.security
    ] = lambda: HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="test-access-token",
    )

    monkeypatch.setattr(
        backend,
        "save_analysis",
        lambda **kwargs: None,
    )

    yield

    ai_quota.reset_ai_quota()
    backend.limiter._storage.reset()
    backend.app.dependency_overrides.pop(
        backend.get_current_user,
        None,
    )
    backend.app.dependency_overrides.pop(
        backend.security,
        None,
    )


def _set_caps(monkeypatch, user_cap, global_cap):
    monkeypatch.setenv("AI_DAILY_USER_CAP", str(user_cap))
    monkeypatch.setenv("AI_DAILY_GLOBAL_CAP", str(global_cap))


def _analyze_payload():
    return {
        "resume": "I know Python.",
        "job_description": "Required: Python FastAPI.",
        "projects": [
            {"name": "Test API", "description": "A Python API project."}
        ],
    }


def _mock_analyze(monkeypatch):
    monkeypatch.setattr(
        backend,
        "run_careergap",
        lambda resume, job_description, projects: {
            "resume_skills": ["Python"],
            "job_skills": ["Python"],
            "matched_skills": ["Python"],
            "missing_skills": [],
            "score": 100.0,
            "github_recommendations": [],
        },
    )
    monkeypatch.setattr(
        backend,
        "generate_career_advice",
        lambda career_gap_data: "Advice.",
    )


# ---------------------------------------------------------------------------
# Unit tests: cap parsing and counters
# ---------------------------------------------------------------------------

def test_missing_env_uses_defaults(monkeypatch):
    monkeypatch.delenv("AI_DAILY_USER_CAP", raising=False)
    monkeypatch.delenv("AI_DAILY_GLOBAL_CAP", raising=False)

    assert ai_quota._read_cap("AI_DAILY_USER_CAP", 30) == 30
    assert ai_quota._read_cap("AI_DAILY_GLOBAL_CAP", 800) == 800


def test_unparsable_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("AI_DAILY_USER_CAP", "not-a-number")

    assert ai_quota._read_cap("AI_DAILY_USER_CAP", 30) == 30


def test_non_positive_env_falls_back_to_default(monkeypatch):
    """Zero or negative caps must never lock every user out."""
    monkeypatch.setenv("AI_DAILY_USER_CAP", "0")
    assert ai_quota._read_cap("AI_DAILY_USER_CAP", 30) == 30

    monkeypatch.setenv("AI_DAILY_USER_CAP", "-5")
    assert ai_quota._read_cap("AI_DAILY_USER_CAP", 30) == 30


def test_per_user_cap_blocks_only_that_user(monkeypatch):
    _set_caps(monkeypatch, user_cap=2, global_cap=100)

    ai_quota.enforce_ai_quota({"sub": "user-a"})
    ai_quota.enforce_ai_quota({"sub": "user-a"})

    with pytest.raises(Exception) as blocked:
        ai_quota.enforce_ai_quota({"sub": "user-a"})
    assert getattr(blocked.value, "status_code", None) == 429

    # A different user still has its own allowance.
    ai_quota.enforce_ai_quota({"sub": "user-b"})


def test_global_cap_blocks_every_user(monkeypatch):
    _set_caps(monkeypatch, user_cap=100, global_cap=3)

    ai_quota.enforce_ai_quota({"sub": "user-a"})
    ai_quota.enforce_ai_quota({"sub": "user-b"})
    ai_quota.enforce_ai_quota({"sub": "user-c"})

    with pytest.raises(Exception) as blocked:
        ai_quota.enforce_ai_quota({"sub": "user-d"})
    assert getattr(blocked.value, "status_code", None) == 429


def test_counters_reset_on_new_utc_day(monkeypatch):
    _set_caps(monkeypatch, user_cap=1, global_cap=100)

    monkeypatch.setattr(ai_quota, "_today", lambda: "2026-11-12")
    ai_quota.enforce_ai_quota({"sub": "user-a"})

    with pytest.raises(Exception) as blocked:
        ai_quota.enforce_ai_quota({"sub": "user-a"})
    assert getattr(blocked.value, "status_code", None) == 429

    monkeypatch.setattr(ai_quota, "_today", lambda: "2026-11-13")
    ai_quota.enforce_ai_quota({"sub": "user-a"})


def test_reset_ai_quota_clears_counters(monkeypatch):
    _set_caps(monkeypatch, user_cap=1, global_cap=100)

    ai_quota.enforce_ai_quota({"sub": "user-a"})
    ai_quota.reset_ai_quota()
    ai_quota.enforce_ai_quota({"sub": "user-a"})


# ---------------------------------------------------------------------------
# Endpoint tests: the quota guards every Groq-backed route
# ---------------------------------------------------------------------------

def test_analyze_returns_429_once_user_cap_is_spent(monkeypatch):
    _set_caps(monkeypatch, user_cap=2, global_cap=100)
    _mock_analyze(monkeypatch)

    assert client.post("/analyze", json=_analyze_payload()).status_code == 200
    assert client.post("/analyze", json=_analyze_payload()).status_code == 200

    blocked = client.post("/analyze", json=_analyze_payload())
    assert blocked.status_code == 429
    assert "Daily AI limit" in blocked.json()["detail"]


def test_analyze_429_does_not_call_the_ai(monkeypatch):
    """A blocked request must not reach the deterministic or AI work."""
    _set_caps(monkeypatch, user_cap=1, global_cap=100)

    calls = {"count": 0}

    def _counting_run(resume, job_description, projects):
        calls["count"] += 1
        return {}

    monkeypatch.setattr(backend, "run_careergap", _counting_run)
    monkeypatch.setattr(
        backend, "generate_career_advice", lambda data: "Advice."
    )

    assert client.post("/analyze", json=_analyze_payload()).status_code == 200
    assert client.post("/analyze", json=_analyze_payload()).status_code == 429
    assert calls["count"] == 1


def test_interview_generate_is_quota_guarded(monkeypatch):
    _set_caps(monkeypatch, user_cap=1, global_cap=100)

    monkeypatch.setattr(
        backend,
        "generate_interview_questions",
        lambda *args, **kwargs: [
            {"type": "technical", "text": "Question?"}
        ],
    )

    payload = {"mode": "quick", "target_role": "Engineer"}

    first = client.post("/interview/generate", json=payload)
    assert first.status_code in (200, 500, 503)

    # The first call consumed the single unit; the next must be 429
    # regardless of what the interview logic would have returned.
    second = client.post("/interview/generate", json=payload)
    assert second.status_code == 429


def test_interview_answer_is_quota_guarded(monkeypatch):
    _set_caps(monkeypatch, user_cap=1, global_cap=100)

    monkeypatch.setattr(
        backend,
        "generate_interview_questions",
        lambda *args, **kwargs: [
            {"type": "technical", "text": "Question?"}
        ],
    )

    # Spend the single unit through a different AI route, proving the
    # cap is shared across AI endpoints for one user.
    client.post(
        "/interview/generate",
        json={"mode": "quick", "target_role": "Engineer"},
    )

    blocked = client.post(
        "/interview/00000000-0000-0000-0000-000000000000/answer",
        json={"answers": [{"question_index": 0, "answer": "text"}]},
    )
    assert blocked.status_code == 429


def test_non_ai_route_has_no_daily_quota():
    """Deterministic routes keep only their per-IP rate limit."""
    response = client.post(
        "/ats/keywords",
        json=_analyze_payload(),
    )
    assert response.status_code == 200
    assert "keywords" in response.json()
