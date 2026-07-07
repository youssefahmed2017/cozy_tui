"""show_traceback(): the full-screen crash-view convenience."""

import cozy_tui.crash_screen as crash_screen
from cozy_tui import App
from cozy_tui.crash_screen import show_traceback


def _make_exc():
    try:
        {"a": 1}["b"]
    except KeyError as exc:
        return exc
    raise AssertionError("unreachable")


def test_show_traceback_builds_and_runs_without_error(monkeypatch):
    # Full=True normally reads the real terminal size; give it a stable one and
    # stop short of the real blocking event loop.
    monkeypatch.setattr(
        "os.get_terminal_size", lambda: __import__("os").terminal_size((80, 24))
    )
    ran = []
    monkeypatch.setattr(App, "run", lambda self: ran.append(self))

    show_traceback(_make_exc())

    assert len(ran) == 1


def test_esc_and_copy_key_are_wired(monkeypatch):
    monkeypatch.setattr(
        "os.get_terminal_size", lambda: __import__("os").terminal_size((80, 24))
    )
    captured = {}

    def fake_run(self):
        captured["app"] = self

    monkeypatch.setattr(App, "run", fake_run)
    show_traceback(_make_exc())

    app = captured["app"]
    from cozy_tui.events import Key

    assert Key.ESC in app._key_handlers
    assert app._key_handlers[Key.ESC]() == "quit"
    assert "c" in app._key_handlers


def test_copy_key_copies_plain_text_traceback(monkeypatch):
    monkeypatch.setattr(
        "os.get_terminal_size", lambda: __import__("os").terminal_size((80, 24))
    )
    captured = {}
    monkeypatch.setattr(App, "run", lambda self: captured.setdefault("app", self))
    copied = []
    monkeypatch.setattr(crash_screen, "copy", lambda text: copied.append(text))

    exc = _make_exc()
    show_traceback(exc)

    app = captured["app"]
    app._key_handlers["c"]()
    assert len(copied) == 1
    assert "KeyError" in copied[0]
