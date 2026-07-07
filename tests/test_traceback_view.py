"""TracebackView: Rich traceback bridged into cozy_tui's cell grid."""

import contextlib
import io

from cozy_tui import App, Style
from cozy_tui._rich_bridge import to_cozy_style
from cozy_tui.widgets import TracebackView
from cozy_tui.widgets.display.traceback_view import format_traceback


def make_app():
    return App(full=False, size="800x300", style=Style(fg="white", bg="black"))


def _make_exc():
    try:
        data = {"a": 1}
        return data["b"]
    except KeyError as exc:
        return exc
    raise AssertionError("unreachable")


def test_natural_height_is_nonzero_and_stable():
    view = TracebackView(0, 0, 60, _make_exc())
    h = view.natural_height(1)
    assert h > 0
    assert view.natural_height(1) == h  # cached, not recomputed differently


def test_rendered_content_mentions_the_exception():
    exc = _make_exc()
    view = TracebackView(0, 0, 60, exc)
    rows = view._rendered_rows(60)
    text = "".join(t for row in rows for t, _ in row)
    assert "KeyError" in text
    assert "Traceback" in text


def test_cache_hits_on_same_width_misses_on_different_width():
    view = TracebackView(0, 0, 60, _make_exc())
    a = view._rendered_rows(60)
    b = view._rendered_rows(60)
    c = view._rendered_rows(40)
    assert a is b
    assert a is not c


def test_draw_writes_into_the_canvas_without_crashing():
    app = make_app()
    view = TracebackView(0, 0, 76, _make_exc())
    app.add(view)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        app.render()
    assert buf.getvalue()  # something was written
    snap = app.snapshot()
    assert "Traceback" in snap


def test_show_locals_false_produces_fewer_rows():
    exc = _make_exc()
    with_locals = TracebackView(0, 0, 60, exc, show_locals=True)
    without_locals = TracebackView(0, 0, 60, exc, show_locals=False)
    assert without_locals.natural_height(1) < with_locals.natural_height(1)


def test_contains_matches_rendered_bounds():
    view = TracebackView(0, 0, 40, _make_exc())
    h = view.natural_height(1)
    assert view.contains(0, 0)
    assert view.contains(39, h - 1)
    assert not view.contains(40, 0)
    assert not view.contains(0, h)


def test_format_traceback_is_plain_text_with_exception_details():
    exc = _make_exc()
    text = format_traceback(exc)
    assert "KeyError" in text
    assert "\x1b" not in text  # no ANSI/styling — plain text for the clipboard


def test_to_cozy_style_handles_none_segment_style():
    # Rich only attaches a Style when one applies; plain segments are None.
    assert to_cozy_style(None).fg is None
    assert to_cozy_style(None).bg is None
