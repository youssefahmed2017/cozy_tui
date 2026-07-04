from cozy_tui import App, Style


def make_app():
    # full=False avoids needing a real terminal; SCALE=10 -> 30x6 grid.
    return App(full=False, size="300x60", style=Style(fg="white", bg="black"))


def row_chars(app, r):
    return [c.char for c in app.buffer[r]]


def test_ascii_write_lands_in_consecutive_cells():
    app = make_app()
    app.clear()
    app.write(0, 0, "hi", app.style)
    assert row_chars(app, 0)[:2] == ["h", "i"]


def test_wide_char_occupies_two_cells_and_shifts_following():
    app = make_app()
    app.clear()
    app.write(0, 0, "aあb", app.style)
    chars = row_chars(app, 0)
    assert chars[0] == "a"
    assert chars[1] == "あ"
    assert chars[2] == ""  # continuation cell for the wide glyph
    assert chars[3] == "b"  # pushed to column 3, not 2


def test_zero_width_char_consumes_no_column():
    app = make_app()
    app.clear()
    app.write(0, 0, "áb", app.style)  # a + combining accent + b
    chars = row_chars(app, 0)
    assert chars[0] == "a"
    assert chars[1] == "b"


def test_out_of_bounds_write_is_ignored():
    app = make_app()
    app.clear()
    app.write(0, 999, "x", app.style)  # below the grid — must not raise
    app.write(-5, 0, "y", app.style)  # left of the grid


def test_render_runs_without_error():
    app = make_app()
    app.write(0, 0, "hello", app.style)
    app.render()  # exercises the diff/full render path against the buffer


def test_snapshot_returns_composed_text():
    app = make_app()
    from cozy_tui.widgets import Label

    app.add(Label(0, 0, "hello"))
    app.add(Label(0, 2, "world"))
    snap = app.snapshot()
    lines = snap.split("\n")
    assert lines[0] == "hello"
    assert lines[1] == ""  # blank row, trailing spaces stripped
    assert lines[2] == "world"


def test_snapshot_does_not_write_to_terminal():
    import contextlib
    import io

    app = make_app()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        app.snapshot()
    assert buf.getvalue() == ""


def test_set_title_emits_osc_sequence():
    import contextlib
    import io

    app = make_app()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        app.set_title("New Title")
    assert buf.getvalue() == "\033]0;New Title\007"
    assert app.title == "New Title"


def test_full_render_uses_crlf_line_breaks():
    # POSIX raw mode disables OPOST, so full-render lines must end with CR+LF or
    # the screen stair-steps. Assert the serialized output has no bare LF.
    import contextlib
    import io

    app = make_app()
    app.write(0, 0, "ab", app.style)
    app.write(0, 1, "cd", app.style)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        app._do_full_render()
    out = buf.getvalue()
    assert "\r\n" in out  # rows separated by CRLF
    assert "\n" not in out.replace("\r\n", "")  # and no lone LF anywhere


def test_setup_disables_and_restores_autowrap():
    # Autowrap (DECAWM) must be off during the run or VTE terminals scroll the
    # screen when the bottom-right cell is written, duplicating the top row.
    for full in (True, False):
        app = App(full=full, size="400x200", style=Style(fg="white", bg="black"))
        enter, exit_ = app._setup_sequences()
        assert "\033[?7l" in enter  # autowrap disabled on entry
        assert "\033[?7h" in exit_  # and restored on exit


def test_setup_picks_motion_mode_from_widgets():
    from cozy_tui.widgets import Button, Label

    plain = App(full=False, size="400x200", style=Style(fg="white", bg="black"))
    plain.add(Label(0, 0, "hi"))
    enter, _ = plain._setup_sequences()
    assert "\033[?1002h" in enter and "\033[?1003h" not in enter  # drag-only

    hovering = App(full=False, size="400x200", style=Style(fg="white", bg="black"))
    hovering.add(Button(0, 0, "Go"))  # Button opts into mouse_moves
    enter, _ = hovering._setup_sequences()
    assert "\033[?1003h" in enter  # any-motion tracking for hover
