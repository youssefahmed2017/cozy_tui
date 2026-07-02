import contextlib
import io
import os

import cozy_tui.app as app_mod
import cozy_tui.widgets.display.markdown as md


def _emit(env, rich_ok):
    """Run _maybe_warn_rich with a forced rich state and env value; return stderr."""
    app_mod._rich_warning_shown = False
    saved_rich, md._RICH_OK = md._RICH_OK, rich_ok
    saved_env = os.environ.get("COZY_TUI_NO_WARNINGS")
    try:
        if env is None:
            os.environ.pop("COZY_TUI_NO_WARNINGS", None)
        else:
            os.environ["COZY_TUI_NO_WARNINGS"] = env
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            app_mod._maybe_warn_rich()
        return buf.getvalue()
    finally:
        md._RICH_OK = saved_rich
        if saved_env is None:
            os.environ.pop("COZY_TUI_NO_WARNINGS", None)
        else:
            os.environ["COZY_TUI_NO_WARNINGS"] = saved_env


def test_no_warning_by_default():
    # Default is COZY_TUI_NO_WARNINGS=1 (warnings off), so unset => silent.
    assert _emit(None, rich_ok=False) == ""


def test_warns_when_explicitly_enabled_and_rich_missing():
    assert "Rich isn't installed" in _emit("0", rich_ok=False)


def test_no_warning_when_rich_present_even_if_enabled():
    assert _emit("0", rich_ok=True) == ""


def test_stays_off_for_truthy_values():
    for value in ("1", "true", "YES", "on"):
        assert _emit(value, rich_ok=False) == ""


def test_enabled_by_falsey_values():
    for value in ("0", "false", "no", "off"):
        assert "Rich isn't installed" in _emit(value, rich_ok=False)


def test_warning_prints_only_once():
    app_mod._rich_warning_shown = False
    saved_rich, md._RICH_OK = md._RICH_OK, False
    saved_env = os.environ.get("COZY_TUI_NO_WARNINGS")
    os.environ["COZY_TUI_NO_WARNINGS"] = "0"  # enable warnings for this test
    try:
        first, second = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(first):
            app_mod._maybe_warn_rich()
        with contextlib.redirect_stderr(second):
            app_mod._maybe_warn_rich()
        assert "Rich isn't installed" in first.getvalue()
        assert second.getvalue() == ""
    finally:
        md._RICH_OK = saved_rich
        app_mod._rich_warning_shown = False
        if saved_env is None:
            os.environ.pop("COZY_TUI_NO_WARNINGS", None)
        else:
            os.environ["COZY_TUI_NO_WARNINGS"] = saved_env
