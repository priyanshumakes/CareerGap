"""Pytest configuration for CareerGap tests.

Sets dummy Supabase credentials before any test modules are imported
to avoid RuntimeError from auth.py module-level check.
"""
import os

# Set dummy Supabase credentials BEFORE any test modules import auth
# This prevents RuntimeError from auth.py module-level check
os.environ.setdefault("SUPABASE_URL", "https://dummy.supabase.co")
os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "dummy-key")

# The daily AI quota (ai_quota.py) defaults to 30 calls per user and
# 800 calls app-wide per day. The whole test suite runs under one or a
# few mocked user ids and fires far more than 30 AI-endpoint calls, so
# the suite raises the caps to effectively unlimited; the quota's own
# tests in tests/test_ai_quota.py set small caps explicitly and reset
# the counters around each check.
os.environ.setdefault("AI_DAILY_USER_CAP", "1000000")
os.environ.setdefault("AI_DAILY_GLOBAL_CAP", "1000000")

# Now safe to import test modules that depend on auth
