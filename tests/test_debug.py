"""App(debug=...): app.debug() logging + the F12 debug-log overlay pane.

Phase 0: a safe print()-equivalent for a raw-mode/alt-screen app (bare print()
would corrupt the display). Phase 1: an in-app viewer for it, toggled by F12.
default_logs: App's own automatic focus/key/click/drag logging on top of it.
"""

import os

from cozy_tui import App, Style
from cozy_tui.events import Key, MouseClick, MouseDrag, MouseMove
from cozy_tui.widgets import Button


def make_app(**kw):
    return App(full=False, size="800x300", style=Style(fg="white", bg="black"), **kw)


# ── Phase 0: app.debug() ──────────────────────────────────────────────────────


def test_debug_is_a_noop_by_default():
    app = make_app()
    app.debug("should not raise or buffer anything")
    assert app._debug_log is None


def test_debug_buffers_when_enabled():
    app = make_app(debug=True)
    app.debug("hello", "world", 42)
    assert list(app._debug_log) == ["hello world 42"]
    assert app._debug_seq == 1


def test_debug_respects_custom_sep():
    app = make_app(debug=True)
    app.debug("a", "b", sep="-")
    assert list(app._debug_log) == ["a-b"]


def test_debug_seq_increments_per_call():
    app = make_app(debug=True)
    app.debug("one")
    app.debug("two")
    assert app._debug_seq == 2


def test_debug_ring_buffer_is_bounded():
    app = make_app(debug=True)
    for i in range(600):
        app.debug(f"line {i}")
    assert len(app._debug_log) == 500
    assert app._debug_log[0] == "line 100"  # oldest 100 evicted
    assert app._debug_log[-1] == "line 599"


def test_debug_log_path_writes_lines_to_a_file(tmp_path):
    path = tmp_path / "debug.log"
    app = make_app(debug=True, debug_log_path=str(path))
    app.debug("to the file")
    app.debug("and another")
    app._debug_file.close()  # normally closed in run()'s finally
    assert path.read_text(encoding="utf-8") == "to the file\nand another\n"


def test_debug_log_path_is_ignored_without_debug_true():
    app = make_app(debug=False, debug_log_path="ignored.log")
    assert app._debug_file is None
    assert not os.path.exists("ignored.log")


# ── Phase 1: the F12 pane ─────────────────────────────────────────────────────


def test_f12_bound_only_when_debug_true():
    assert Key.F12 in make_app(debug=True)._key_handlers
    assert Key.F12 not in make_app(debug=False)._key_handlers


def test_f12_handler_is_the_public_toggle_method():
    # So other code (a menu item, a button, a custom key binding) can trigger
    # the same pane without reaching into a private method.
    app = make_app(debug=True)
    assert app._key_handlers[Key.F12] == app.toggle_debug_pane


def test_toggle_debug_pane_is_a_noop_without_debug_true():
    app = make_app(debug=False)
    app.toggle_debug_pane()  # must not raise
    assert app._debug_pane is None
    assert app._overlays == []


def test_f12_opens_and_closes_the_pane():
    app = make_app(debug=True)
    toggle = app._key_handlers[Key.F12]

    toggle()
    assert app._debug_pane is not None
    assert len(app._overlays) == 1
    # Focus dives into the pane's scrollable log (Box.focusable=False, so the
    # Box itself is skipped), so Up/Down scroll it, not the app underneath.
    assert getattr(app.focused, "scrollable", False)

    toggle()
    assert app._debug_pane is None
    assert len(app._overlays) == 0


def test_debug_pane_picks_up_the_apps_theme():
    # Regression: DebugPane used to be built with Box's bare default style
    # instead of the app's, so it never reflected the active theme.
    app = make_app(debug=True)
    app.style.bg = "magenta_bg"
    app.toggle_debug_pane()
    assert app._debug_pane.style is app.style


def test_pane_shows_buffered_lines_and_syncs_live():
    app = make_app(debug=True)
    app.debug("line one")
    app.debug("line two")

    app._key_handlers[Key.F12]()
    snap = app.snapshot()
    assert "line one" in snap
    assert "line two" in snap

    app.debug("line three")
    app._compose()
    assert "line three" in app.snapshot()


def test_esc_closes_the_pane_via_the_normal_modal_path():
    app = make_app(debug=True)
    app._key_handlers[Key.F12]()
    modal = app._topmost_modal()
    assert modal is not None and modal.close_on_escape
    app.close_overlay(modal.widget)
    assert app._debug_pane is None


# ── default_logs: App's own automatic focus/key/click/drag logging ──────────


def test_default_logs_on_by_default_when_debug_true():
    assert make_app(debug=True)._default_logs is True


def test_default_logs_false_disables_auto_logging():
    app = make_app(debug=True, default_logs=False)
    b = Button(0, 0, "Go")
    app.add(b)
    app.focus(b)
    app._dispatch_mouse(MouseClick(0, 0, 0))
    assert list(app._debug_log) == []


def test_focus_change_is_logged():
    app = make_app(debug=True)
    b = Button(0, 0, "Go")
    app.add(b)
    app.focus(b)
    assert any("Focused on widget" in line for line in app._debug_log)


def test_click_is_logged_with_coordinates():
    app = make_app(debug=True)
    app._dispatch_mouse(MouseClick(5, 7, 0))
    assert "Clicked on col: 5, row: 7" in list(app._debug_log)


def test_drag_is_logged_with_coordinates():
    app = make_app(debug=True)
    app._dispatch_mouse(MouseDrag(3, 4, 0))
    assert "Dragged mouse on col: 3, row: 4" in list(app._debug_log)


def test_mouse_move_is_not_logged():
    # Deliberately excluded — it fires far too often to be useful in the log.
    app = make_app(debug=True)
    app._dispatch_mouse(MouseMove(1, 1))
    assert list(app._debug_log) == []


def test_scroll_wheel_is_not_logged_as_a_key_press(monkeypatch):
    # Wheel scroll arrives through the same path as a key press (Key.SCROLL_UP/
    # DOWN are plain string constants, not Mouse* instances) but isn't one —
    # drive real iterations of run()'s loop to exercise the actual check.
    # (Key.SCROLL_UP is consumed by app.py's own scroll-handling branch before
    # reaching _key_handlers, so quit() is triggered directly on read #2.)
    import cozy_tui.app as appmod

    app = make_app(debug=True, catch_errors=False)
    reads = {"n": 0}

    def fake_read_key():
        reads["n"] += 1
        if reads["n"] == 1:
            return Key.SCROLL_UP
        app.quit()
        return None

    monkeypatch.setattr(appmod, "kbhit", lambda: True)
    monkeypatch.setattr(appmod, "read_key", fake_read_key)

    app.run()

    assert reads["n"] == 2
    assert list(app._debug_log) == []
