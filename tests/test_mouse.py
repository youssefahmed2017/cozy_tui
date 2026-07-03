import cozy_tui.events as ev
from cozy_tui import App, Style
from cozy_tui.events import (
    Key,
    MouseClick,
    MouseDrag,
    MouseMove,
    MouseRelease,
)
from cozy_tui.widget import Widget


def feed(seq: str):
    """Prime the internal read buffer and parse one event (stdin untouched)."""
    ev._buf = list(seq)
    return ev.read_key()


# ── SGR mouse parsing ─────────────────────────────────────────────────────────


def test_press_parses_to_click():
    e = feed("\x1b[<0;5;3M")  # left button, 1-indexed col 5 row 3
    assert isinstance(e, MouseClick)
    assert (e.col, e.row, e.btn) == (4, 2, 0)


def test_release_parses_to_release():
    e = feed("\x1b[<0;5;3m")  # lowercase m = release
    assert isinstance(e, MouseRelease)
    assert (e.col, e.row, e.btn) == (4, 2, 0)


def test_motion_with_button_is_drag():
    e = feed("\x1b[<32;5;3M")  # 32 = motion flag, low bits 0 = left held
    assert isinstance(e, MouseDrag)
    assert (e.col, e.row, e.btn) == (4, 2, 0)


def test_motion_without_button_is_move():
    e = feed("\x1b[<35;5;3M")  # 32 motion + low bits 3 = no button held
    assert isinstance(e, MouseMove)
    assert (e.col, e.row) == (4, 2)


def test_wheel_still_maps_to_scroll_keys():
    assert feed("\x1b[<64;5;3M") == Key.SCROLL_UP
    assert feed("\x1b[<65;5;3M") == Key.SCROLL_DOWN


def test_sequence_split_on_esc_is_not_misread_as_escape():
    # A bulk read can end exactly on the ESC that begins the next sequence
    # (e.g. a mouse-motion flood). read_key must wait for the continuation
    # instead of firing Key.ESC (which, bound to quit, closed apps instantly).
    orig_read, orig_wait = ev.os.read, ev._console.wait_input
    try:
        ev._buf = list("\x1b")           # chunk ended right on the ESC
        rest = list("[<35;5;3M")         # continuation: a MouseMove
        ev.os.read = lambda fd, n: ("".join(rest), rest.clear())[0].encode()
        ev._console.wait_input = lambda t: True   # continuation is pending
        e = ev.read_key()
        assert isinstance(e, MouseMove)
        assert (e.col, e.row) == (4, 2)
    finally:
        ev.os.read, ev._console.wait_input = orig_read, orig_wait
        ev._buf = []


def test_lone_escape_still_returns_escape():
    orig_wait = ev._console.wait_input
    try:
        ev._console.wait_input = lambda t: False  # nothing follows the ESC
        ev._buf = list("\x1b")
        assert ev.read_key() == Key.ESC
    finally:
        ev._console.wait_input = orig_wait
        ev._buf = []


# ── app dispatch ──────────────────────────────────────────────────────────────


class Recorder(Widget):
    focusable = True

    def __init__(self, x, y, w, h):
        super().__init__(x, y)
        self._w, self._h = w, h
        self.events = []

    def contains(self, col, row):
        return self.x <= col < self.x + self._w and self.y <= row < self.y + self._h

    def draw(self, canvas):
        pass


def make_app():
    return App(full=False, size="300x60", style=Style(fg="white", bg="black"))


def test_registration_callbacks_fire():
    app = make_app()
    w = Recorder(0, 0, 10, 5)
    fired = []
    w.on_click(lambda widget: fired.append("click"))
    w.on_release(lambda widget, c, r: fired.append(("release", c, r)))
    w.on_drag(lambda widget, c, r: fired.append(("drag", c, r)))
    app.add(w)

    app._dispatch_mouse(MouseClick(2, 1, 0))
    assert app.focused is w
    app._dispatch_mouse(MouseDrag(3, 1, 0))
    app._dispatch_mouse(MouseRelease(3, 1, 0))
    assert fired == ["click", ("drag", 3, 1), ("release", 3, 1)]


def test_double_click_detected_and_falls_back_to_click():
    app = make_app()
    w = Recorder(0, 0, 10, 5)
    seen = []
    w.on_click(lambda widget: seen.append("click"))
    w.on_double_click(lambda widget: seen.append("double"))
    app.add(w)

    app._dispatch_mouse(MouseClick(2, 1, 0))  # first click
    app._dispatch_mouse(MouseClick(2, 1, 0))  # quick second → double
    assert seen == ["click", "double"]

    # A widget with no double handler gets a plain click on the second press.
    plain = Recorder(0, 0, 10, 5)
    hits = []
    plain.on_click(lambda widget: hits.append("click"))
    app2 = make_app()
    app2.add(plain)
    app2._dispatch_mouse(MouseClick(1, 1, 0))
    app2._dispatch_mouse(MouseClick(1, 1, 0))
    assert hits == ["click", "click"]


def test_double_click_requires_same_button_and_target():
    app = make_app()
    w = Recorder(0, 0, 10, 5)
    seen = []
    w.on_click(lambda widget: seen.append("click"))
    w.on_double_click(lambda widget: seen.append("double"))
    app.add(w)

    app._dispatch_mouse(MouseClick(2, 1, 0))  # left
    app._dispatch_mouse(MouseClick(2, 1, 2))  # right → not a double
    assert seen == ["click", "click"]


def test_hover_dispatched_without_changing_focus():
    app = make_app()
    w = Recorder(0, 0, 10, 5)
    moves = []
    w.on_hover(lambda widget, c, r: moves.append((c, r)))
    app.add(w)

    app._dispatch_mouse(MouseMove(4, 2))
    assert moves == [(4, 2)]
    assert app.focused is None  # hover must not steal focus


def test_global_mouse_hook_can_consume():
    app = make_app()
    w = Recorder(0, 0, 10, 5)
    w.on_click(lambda widget: w.events.append("click"))
    app.add(w)

    got = []
    app.on_mouse(lambda event: got.append(event) or True)  # consume everything
    app._dispatch_mouse(MouseClick(2, 1, 0))
    assert len(got) == 1
    assert w.events == []  # consumed → widget never saw it
    assert app.focused is None


def test_global_mouse_hook_sees_scrolled_coordinates():
    app = make_app()
    app.scroll_y = 5
    seen = []
    app.on_mouse(lambda event: seen.append(event.row) or True)
    app._dispatch_mouse(MouseClick(0, 1, 0))
    assert seen == [6]  # 1 + scroll_y
