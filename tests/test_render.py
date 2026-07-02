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
