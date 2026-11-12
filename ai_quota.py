"""Daily quota for AI-backed endpoints.

CareerGap's AI features run on Groq's free plan, whose daily request
allowance is shared by every user of the app. The per-IP rate limits
in backend.py slow a single client down, but they do not stop a
script that rotates IPs or signs up many accounts: each new account
gets a fresh per-IP budget and the aggregate can still drain the
whole free quota, taking AI features down for everyone until Groq's
limit resets.

This module adds two daily counters on top of the per-IP limits:

- a per-user cap (AI_DAILY_USER_CAP, default 30 AI calls per UTC
  day), so one account cannot burn the quota alone, and
- a global cap (AI_DAILY_GLOBAL_CAP, default 800 AI calls per UTC
  day), so many accounts together cannot exceed what the free plan
  can serve; Groq's own hard limit would otherwise reject every
  caller with no clear message.

Both counters are in-memory and per-process. On Render's free plan
that means they reset on every deploy, restart, or cold start, so on
a restart day a user can get a fresh allowance earlier than 24 hours.
That is accepted on purpose: the quota exists to protect the shared
free Groq allowance from scripted abuse, not to meter honest users
precisely, and adding a database table for exactness is not worth the
complexity at this scale. If the app ever runs more than one backend
instance, each instance counts independently (caps are effectively
multiplied), which a database-backed counter would fix.

A request consumes one unit when it passes the quota check, before
the AI call runs. If the AI call then fails (timeout, provider
error), the unit is still consumed. That is deliberate: counting
only successful calls would let a client retry-loop on failures
without ever spending quota.
"""

import os
import threading
from datetime import datetime, timezone

from fastapi import Depends, HTTPException

from auth import get_current_user

DEFAULT_USER_CAP = 30
DEFAULT_GLOBAL_CAP = 800

_lock = threading.Lock()
_day = None
_user_counts = {}
_global_count = 0


def _read_cap(name, default):
    """Parse a positive integer cap from the environment.

    Missing, unparsable, or non-positive values fall back to the
    default so a misconfigured environment can never disable the
    quota or lock every user out.
    """
    raw = os.getenv(name)

    if raw is None:
        return default

    try:
        value = int(raw)
    except ValueError:
        return default

    return value if value > 0 else default


def _today():
    """Current UTC day; the quota window resets at UTC midnight."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def reset_ai_quota():
    """Clear every counter. Used by tests; harmless in production."""
    global _day, _user_counts, _global_count

    with _lock:
        _day = None
        _user_counts = {}
        _global_count = 0


def enforce_ai_quota(claims: dict = Depends(get_current_user)) -> dict:
    """FastAPI dependency that consumes one unit of the daily quota.

    Raises 429 when the caller's per-user cap or the app-wide cap for
    today is exhausted. Otherwise consumes one unit and returns the
    caller's claims so endpoints can reuse them.
    """
    global _day, _user_counts, _global_count

    user_id = str(claims.get("sub") or "unknown")
    user_cap = _read_cap("AI_DAILY_USER_CAP", DEFAULT_USER_CAP)
    global_cap = _read_cap("AI_DAILY_GLOBAL_CAP", DEFAULT_GLOBAL_CAP)
    today = _today()

    with _lock:
        if _day != today:
            _day = today
            _user_counts = {}
            _global_count = 0

        used = _user_counts.get(user_id, 0)

        if used >= user_cap:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Daily AI limit reached for this account. "
                    "It resets at midnight UTC."
                ),
            )

        if _global_count >= global_cap:
            raise HTTPException(
                status_code=429,
                detail=(
                    "CareerGap's AI capacity for today is fully "
                    "used. It resets at midnight UTC."
                ),
            )

        _user_counts[user_id] = used + 1
        _global_count += 1

    return claims
