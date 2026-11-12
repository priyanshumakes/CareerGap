"""Tests for the Turnstile (bot check) wiring on the auth pages.

The feature ships configured OFF: turnstile-config.js carries an
empty site key, no widget renders, no captcha token is sent, and the
pages behave exactly as before until a real site key is pasted in
and CAPTCHA is enabled in Supabase (docs/bot-protection-setup.md).
These tests pin that safe-by-default behavior and the wiring that
activates once a key is set.
"""

from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

TURNSTILE_JS = FRONTEND_DIR / "turnstile-config.js"
SIGNUP_HTML = FRONTEND_DIR / "signup.html"
SIGNUP_JS = FRONTEND_DIR / "signup.js"
LOGIN_HTML = FRONTEND_DIR / "login.html"
LOGIN_JS = FRONTEND_DIR / "login.js"
LOGIN_CSS = FRONTEND_DIR / "login.css"
HEADERS = FRONTEND_DIR / "_headers"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Safe-by-default configuration
# ---------------------------------------------------------------------------

def test_site_key_is_empty_by_default():
    """A real key must be pasted deliberately; nothing half-activates."""
    config = _read(TURNSTILE_JS)

    assert 'CAREERGAP_TURNSTILE_SITE_KEY = ""' in config


def test_no_widget_or_script_when_unconfigured():
    config = _read(TURNSTILE_JS)

    # Disabled state must resolve without loading anything external.
    assert "Promise.resolve(false)" in config
    # The Turnstile API script is injected on demand, never as a
    # static tag, so an unconfigured page makes zero external calls.
    assert "challenges.cloudflare.com/turnstile/v0/api.js" in config
    assert "document.createElement(\"script\")" in config

    for page in ("signup.html", "login.html"):
        html = _read(FRONTEND_DIR / page)
        assert "challenges.cloudflare.com" not in html


def test_secret_key_is_never_in_the_frontend():
    """Only the public site key may appear; the secret lives in
    Supabase and must never be committed."""
    for path in FRONTEND_DIR.iterdir():
        if path.suffix in (".js", ".html", ".css"):
            text = _read(path)
            assert "TURNSTILE_SECRET" not in text
            assert "secret_key" not in text.lower().replace(
                "secret keys", ""
            )


# ---------------------------------------------------------------------------
# Page wiring
# ---------------------------------------------------------------------------

def test_config_script_loaded_before_page_scripts():
    signup = _read(SIGNUP_HTML)
    assert signup.index("turnstile-config.js") < signup.index(
        "signup.js"
    )

    login = _read(LOGIN_HTML)
    assert login.index("turnstile-config.js") < login.index(
        "login.js"
    )


def test_widget_containers_exist_above_the_buttons():
    signup = _read(SIGNUP_HTML)
    container = signup.index('id="turnstile-container"')
    # The <title> also says "Create Account"; the button comes
    # after the container.
    button = signup.index("Create Account", container)
    assert container < button

    login = _read(LOGIN_HTML)
    login_container = login.index('id="turnstile-login-container"')
    login_button = login.index("Sign In", login_container)
    assert login_container < login_button

    recovery_container = login.index(
        'id="turnstile-recovery-container"'
    )
    recovery_button = login.index("Send reset link")
    assert recovery_container < recovery_button


def test_empty_container_takes_no_space():
    css = _read(LOGIN_CSS)
    assert ".turnstile-container" in css
    assert ".turnstile-container:empty" in css


# ---------------------------------------------------------------------------
# Token handling
# ---------------------------------------------------------------------------

def test_signup_requires_and_sends_captcha_token_when_enabled():
    js = _read(SIGNUP_JS)

    assert "careerGapTurnstileRender(\"turnstile-container\")" in js
    assert "careerGapTurnstileEnabled()" in js
    assert "careerGapTurnstileToken(turnstileWidgetId)" in js
    assert "Please complete the bot check." in js
    assert "signUpOptions.captchaToken = captchaToken" in js
    # The token goes inside signUp's options object.
    assert "options: signUpOptions" in js
    # Tokens are single-use: the widget resets after a failed attempt.
    assert "careerGapTurnstileReset(turnstileWidgetId)" in js


def test_login_requires_and_sends_captcha_token_when_enabled():
    js = _read(LOGIN_JS)

    assert 'careerGapTurnstileRender("turnstile-login-container")' in js
    assert "signInOptions.captchaToken = captchaToken" in js
    assert "options: signInOptions" in js
    assert "careerGapTurnstileReset(\n                    loginTurnstileWidgetId\n                )" in js


def test_password_recovery_sends_captcha_token_when_enabled():
    """Password reset is an anonymous flow too; Supabase applies the
    same CAPTCHA check to it, so it must send a token or reset breaks
    the moment CAPTCHA is enabled."""
    js = _read(LOGIN_JS)

    assert 'careerGapTurnstileRender("turnstile-recovery-container")' in js
    assert "recoveryOptions.captchaToken = captchaToken" in js
    assert "resetPasswordForEmail(\n                            recoveryEmail,\n                            recoveryOptions\n                        )" in js


def test_csp_allows_turnstile():
    """The report-only CSP must list Turnstile's domains so the report
    stays clean and a future enforcing policy does not break auth."""
    headers = _read(HEADERS)

    assert (
        "script-src 'self' https://cdn.jsdelivr.net "
        "https://challenges.cloudflare.com" in headers
    )
    assert "frame-src https://challenges.cloudflare.com" in headers
    assert "https://challenges.cloudflare.com" in headers.split(
        "connect-src"
    )[1]
