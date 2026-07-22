"""The public test harness (cozy_tui/testing.py)."""

import time

import pytest

from cozy_tui import App, Style
from cozy_tui.events import Key
from cozy_tui.testing import Harness
from cozy_tui.widgets import Box, Button, Input, Label, ListView


def make_app(**kw):
    kw.setdefault("size", "600x200")
    return App(full=False, style=Style(fg="white", bg="black"), **kw)


@pytest.fixture
def ui():
    app = make_app()
    app.add(Label(0, 0, "Hello"))
    return Harness(app)


# ── reading the screen ───────────────────────────────────────────────────────


def test_screen_reflects_the_composed_ui(ui):
    assert "Hello" in ui.screen
    assert ui.line(0) == "Hello"


def test_lines_covers_every_row(ui):
    assert len(ui.lines) == ui.app.rows


def test_find_locates_text(ui):
    assert ui.find("Hello") == (0, 0)
    assert ui.find("nope") is None


def test_contains_shorthand(ui):
    assert "Hello" in ui
    assert "Goodbye" not in ui


def test_cell_exposes_style(ui):
    app = make_app()
    app.add(Label(0, 0, "X", Style(fg="red")))
    harness = Harness(app)
    assert harness.cell(0, 0).char == "X"
    assert harness.cell(0, 0).style.fg == "red"


def test_composing_is_silent(capsys):
    # The whole point of composing rather than render()ing: a test suite must
    # not be interleaved with thousands of escape sequences.
    app = make_app()
    app.add(Label(0, 0, "quiet"))
    harness = Harness(app)
    harness.press("a").click((0, 0))
    assert capsys.readouterr().out == ""


# ── setup ────────────────────────────────────────────────────────────────────


def test_a_full_screen_app_is_forced_headless():
    # Otherwise the buffer would be sized from the real terminal and every
    # assertion would depend on the machine running the test.
    app = App(full=True)
    harness = Harness(app, size="400x100")
    assert app.full is False
    assert (app.cols, app.rows) == (40, 10)
    assert len(harness.lines) == 10


def test_errors_propagate_instead_of_opening_a_crash_screen():
    app = make_app()  # catch_errors defaults to True
    boom = Button(0, 0, "Boom")
    boom.on_click(lambda _b: 1 / 0)
    app.add(boom)
    ui = Harness(app)
    assert app.catch_errors is False
    with pytest.raises(ZeroDivisionError):
        ui.click(boom)


def test_works_as_a_context_manager():
    app = make_app()
    app.add(Label(0, 0, "hi"))
    with Harness(app) as ui:
        assert "hi" in ui
    assert app._should_quit is True


# ── keyboard ─────────────────────────────────────────────────────────────────


def test_type_enters_text_into_the_focused_input():
    app = make_app()
    field = Input(0, 0, 20)
    app.add(field)
    ui = Harness(app).focus(field)
    ui.type("hello")
    assert field.value == "hello"
    assert "hello" in ui


def test_type_fires_per_character_handlers():
    app = make_app()
    field = Input(0, 0, 20)
    seen = []
    field.on_change(seen.append)
    app.add(field)
    Harness(app).focus(field).type("abc")
    assert seen == ["a", "ab", "abc"]


def test_paste_arrives_as_one_event():
    app = make_app()
    field = Input(0, 0, 20)
    seen = []
    field.on_change(seen.append)
    app.add(field)
    Harness(app).focus(field).paste("hello")
    assert field.value == "hello"
    assert seen == ["hello"]  # one event, not five


def test_press_sends_key_constants():
    app = make_app()
    first, second = Button(0, 0, "A"), Button(0, 2, "B")
    app.add(first)
    app.add(second)
    ui = Harness(app).focus(first)
    ui.press(Key.TAB)
    assert ui.focused is second
    ui.press(Key.SHIFT_TAB)
    assert ui.focused is first


def test_press_accepts_several_keys_at_once():
    app = make_app()
    field = Input(0, 0, 20)
    app.add(field)
    ui = Harness(app).focus(field)
    ui.press("a", "b", Key.BACKSPACE)
    assert field.value == "a"


# ── mouse ────────────────────────────────────────────────────────────────────


def test_click_activates_a_button():
    app = make_app()
    status = Label(0, 2, "Ready")
    button = Button(0, 0, "Save")
    button.on_click(lambda _b: setattr(status, "text", "Saved!"))
    app.add(button)
    app.add(status)
    ui = Harness(app)
    ui.click(button)
    assert "Saved!" in ui


def test_click_accepts_explicit_coordinates():
    app = make_app()
    button = Button(3, 1, "Go")
    hits = []
    button.on_click(lambda _b: hits.append(1))
    app.add(button)
    Harness(app).click((3, 1))
    assert hits == [1]


def test_click_moves_focus_like_a_real_click():
    app = make_app()
    field = Input(0, 0, 20)
    app.add(field)
    ui = Harness(app)
    ui.click(field)
    assert ui.focused is field


def test_right_click_fires_the_right_click_handler():
    app = make_app()
    seen = []
    label = Label(0, 0, "target")
    label.focusable = True
    label.on_right_click(lambda _w, c, r: seen.append((c, r)))
    app.add(label)
    Harness(app).right_click(label)
    assert seen == [(0, 0)]


def test_double_click_fires_the_double_click_handler():
    app = make_app()
    seen = []
    button = Button(0, 0, "Go")
    button.on_double_click(lambda _w: seen.append("double"))
    app.add(button)
    Harness(app).double_click(button)
    assert seen == ["double"]


def test_hover_fires_enter_and_leave():
    app = make_app()
    events = []
    button = Button(0, 0, "Go")
    button.on_enter(lambda _w: events.append("enter"))
    button.on_leave(lambda _w: events.append("leave"))
    app.add(button)
    ui = Harness(app)
    ui.hover(button)
    ui.hover((0, 5))
    assert events == ["enter", "leave"]


def test_drag_selects_text_in_an_input():
    app = make_app()
    field = Input(0, 0, 20)
    field.value = "hello world"
    app.add(field)
    ui = Harness(app)
    ui.click(field).drag((5, 0))
    assert field._sel_text() == "hello"
    ui.release((5, 0))


def test_scroll_moves_a_list():
    app = make_app()
    items = ListView(0, 0, height=3)
    for i in range(20):
        items.append(f"row {i}")
    app.add(items)
    ui = Harness(app)
    before = items._scroll_off
    ui.scroll(items, down=True, amount=5)
    assert items._scroll_off >= before


# ── focus ────────────────────────────────────────────────────────────────────


def test_focus_sets_and_reports_the_focused_widget():
    app = make_app()
    field = Input(0, 0, 20)
    app.add(field)
    ui = Harness(app)
    assert ui.focused is None
    ui.focus(field)
    assert ui.focused is field


def test_cursor_reports_the_terminal_cursor_position():
    app = make_app()
    field = Input(0, 1, 20)
    field.value = "abc"
    field.cursor_pos = 3
    app.add(field)
    ui = Harness(app).focus(field)
    assert ui.cursor == (3, 1)


def test_cursor_is_none_with_nothing_focused(ui):
    assert ui.cursor is None


# ── time ─────────────────────────────────────────────────────────────────────


def test_advance_fires_a_one_shot_timer():
    app = make_app()
    status = Label(0, 0, "waiting")
    app.add(status)
    app.after(30, lambda: setattr(status, "text", "done"))
    ui = Harness(app)
    assert "waiting" in ui
    ui.advance(29)
    assert "waiting" in ui  # not yet
    ui.advance(2)
    assert "done" in ui  # 30s tested instantly, nothing slept


def test_advance_accumulates_across_calls():
    app = make_app()
    ticks = []
    app.every(1, lambda: ticks.append(1))
    ui = Harness(app)
    for _ in range(3):
        ui.advance(1)
    assert len(ticks) == 3


def test_advance_does_not_sleep():
    app = make_app()
    app.after(60, lambda: None)
    started = time.monotonic()
    Harness(app).advance(60)
    assert time.monotonic() - started < 1.0


# ── background work ──────────────────────────────────────────────────────────


def test_settle_delivers_a_worker_result_on_this_thread():
    app = make_app()
    status = Label(0, 0, "loading")
    app.add(status)
    seen_thread = []

    def work():
        return "loaded"

    def done(value):
        seen_thread.append(__import__("threading").current_thread())
        status.text = value

    ui = Harness(app)
    app.run_worker(work, on_result=done)
    ui.settle()
    assert "loaded" in ui
    assert seen_thread[0] is __import__("threading").current_thread()


def test_settle_delivers_worker_errors():
    app = make_app()
    errors = []
    ui = Harness(app)
    app.run_worker(lambda: 1 / 0, on_error=errors.append)
    ui.settle()
    assert isinstance(errors[0], ZeroDivisionError)


def test_settle_gives_up_after_its_timeout():
    app = make_app()
    started = time.monotonic()
    Harness(app).settle(timeout=0.05)  # nothing running
    assert time.monotonic() - started < 1.0


# ── misc ─────────────────────────────────────────────────────────────────────


def test_resize_reflows_a_docked_layout():
    app = make_app()
    box = Box(0, 0, "10x10", title="side")
    app.dock(box, "fill")
    ui = Harness(app)
    wide = len(ui.line(0))
    ui.resize("300x100")
    assert (app.cols, app.rows) == (30, 10)
    assert len(ui.line(0)) != wide


def test_quit_requested_reports_app_quit():
    app = make_app()
    button = Button(0, 0, "Quit")
    button.on_click(lambda _b: app.quit())
    app.add(button)
    ui = Harness(app)
    assert ui.quit_requested is False
    ui.click(button)
    assert ui.quit_requested is True


def test_actions_chain():
    app = make_app()
    field = Input(0, 0, 20)
    app.add(field)
    ui = Harness(app)
    ui.focus(field).type("ab").press(Key.BACKSPACE).type("c")
    assert field.value == "ac"
