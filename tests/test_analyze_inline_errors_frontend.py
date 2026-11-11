"""Regression tests for the Analyze form's inline validation errors.

The Analyze form used to report missing input with alert(). A modal
dialog blocks the page's JavaScript while it is open, so any browser
or driver that does not answer it sees a frozen tab - the exact
symptom seen in the 2026-11-11 smoke test. The form now shows the
same messages inline under the Analyze button, focuses the offending
field, and clears the message as soon as the user edits the form.
"""

import re
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
SCRIPT_JS = FRONTEND_DIR / "script.js"
STYLE_CSS = FRONTEND_DIR / "style.css"
INDEX_HTML = FRONTEND_DIR / "index.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _analyze_handler(js: str) -> str:
    start = js.index('analyzeButton.addEventListener(\n            "click"')
    end = js.index("// INITIALIZE", start)
    return js[start:end]


def test_analyze_form_has_no_blocking_alerts():
    handler = _analyze_handler(_read(SCRIPT_JS))
    assert "alert(" not in handler, (
        "the Analyze handler must not freeze the page with alert()"
    )
    for message in (
        "Please enter your resume or upload a resume file.",
        "Please enter the target job description or upload a job description file.",
        "Please complete every project name and description.",
    ):
        assert message in handler


def test_status_element_is_present_and_announced():
    html = _read(INDEX_HTML)
    assert html.count('id="analyze-status"') == 1
    start = html.index('id="analyze-status"')
    tag = html[html.rindex("<", 0, start):html.index(">", start) + 1]
    assert 'role="alert"' in tag
    assert 'aria-live="polite"' in tag
    assert "analyze-status" in tag

    # The status line sits directly under the Analyze button.
    assert html.index('id="analyze-button"') < start


def test_handler_reports_inline_and_focuses_the_field():
    handler = _analyze_handler(_read(SCRIPT_JS))
    assert handler.count("showAnalyzeError(") == 3
    assert "resumeInput" in handler
    assert "jobDescriptionInput" in handler
    # The project branch focuses the first empty project field.
    assert "emptyProjectField" in handler
    assert "field.focus()" in _read(SCRIPT_JS)


def test_message_clears_on_click_and_on_edit():
    js = _read(SCRIPT_JS)
    handler = _analyze_handler(js)
    assert "clearAnalyzeError();" in handler
    assert re.search(
        r'analyzeSection\.addEventListener\(\s*"input",\s*clearAnalyzeError\s*\)',
        js,
    ), "editing the form must clear the validation message"


def test_status_styles_are_token_driven():
    css = _read(STYLE_CSS)
    start = css.index(".analyze-status {")
    open_index = css.index("{", start)
    close_index = css.index("}", open_index)
    rule = css[start:close_index + 1]
    assert "min-height: 20px;" in rule
    assert "color: var(--olive-soft);" in rule
    assert "#" not in rule

    err_start = css.index(".analyze-status.error {")
    err_open = css.index("{", err_start)
    err_close = css.index("}", err_open)
    err_rule = css[err_start:err_close + 1]
    assert "color: var(--error-red);" in err_rule
    assert "#" not in err_rule

    assert css.count("{") == css.count("}")
