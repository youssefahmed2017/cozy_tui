from cozy_tui import App, Style
from cozy_tui.events import Key, MouseClick
from cozy_tui.testing import Harness
from cozy_tui.widgets import ConfirmDialog


def make_ui(size="800x200"):
    return Harness(App(full=False, size=size, style=Style(fg="white", bg="black")))


# ── App.confirm() ────────────────────────────────────────────────────────────


def test_confirm_opens_as_focused_modal():
    ui = make_ui()
    app = ui.app
    dlg = app.confirm("Continue?")
    assert isinstance(dlg, ConfirmDialog)
    assert app._topmost_modal() is not None
    assert app.focused is dlg
    assert dlg.message == "Continue?"


def test_default_true_highlights_yes():
    ui = make_ui()
    app = ui.app
    dlg = app.confirm("Continue?", default=True)
    assert dlg._yes is True
    dlg2 = app.confirm("Continue?", default=False)
    assert dlg2._yes is False


def test_enter_picks_the_highlighted_default_and_closes():
    ui = make_ui()
    app = ui.app
    events = []
    app.confirm(
        "Continue?",
        on_yes=lambda: events.append("yes"),
        on_no=lambda: events.append("no"),
    )
    ui.press(Key.ENTER)
    assert events == ["yes"]
    assert app._topmost_modal() is None


def test_left_toggles_the_highlight_before_choosing():
    ui = make_ui()
    app = ui.app
    events = []
    app.confirm(
        "Continue?",
        default=True,
        on_yes=lambda: events.append("yes"),
        on_no=lambda: events.append("no"),
    )
    ui.press(Key.LEFT)
    ui.press(Key.ENTER)
    assert events == ["no"]


def test_y_and_n_choose_directly_without_toggling_first():
    ui = make_ui()
    app = ui.app
    events = []
    app.confirm(
        "Continue?",
        on_yes=lambda: events.append("yes"),
        on_no=lambda: events.append("no"),
    )
    ui.press("n")
    assert events == ["no"]

    events2 = []
    app.confirm(
        "Continue?",
        default=False,
        on_yes=lambda: events2.append("yes"),
        on_no=lambda: events2.append("no"),
    )
    ui.press("y")
    assert events2 == ["yes"]


def test_cancel_fires_on_no_not_on_yes():
    ui = make_ui()
    app = ui.app
    events = []
    app.confirm(
        "Continue?",
        on_yes=lambda: events.append("yes"),
        on_no=lambda: events.append("no"),
    )
    app.close_overlay()  # simulates Esc / click-outside dismissal
    assert events == ["no"]


def test_choosing_does_not_also_fire_cancel():
    ui = make_ui()
    app = ui.app
    events = []
    app.confirm(
        "Continue?",
        on_yes=lambda: events.append("yes"),
        on_no=lambda: events.append("no"),
    )
    ui.press(Key.ENTER)  # default=True -> yes
    assert events == ["yes"]  # on_no must not also fire


def test_click_on_no_button_selects_it():
    ui = make_ui()
    app = ui.app
    events = []
    dlg = app.confirm(
        "Continue?",
        on_yes=lambda: events.append("yes"),
        on_no=lambda: events.append("no"),
    )
    ui.screen
    _text, start, _end, _is_yes = dlg._button_spans(dlg.width)[1]
    col = dlg.abs_x + 1 + start + 1
    row = dlg.abs_y + 2
    ui.click((col, row))
    assert events == ["no"]


def test_click_on_yes_button_selects_it():
    ui = make_ui()
    app = ui.app
    events = []
    dlg = app.confirm(
        "Continue?",
        default=False,
        on_yes=lambda: events.append("yes"),
        on_no=lambda: events.append("no"),
    )
    ui.screen
    _text, start, _end, _is_yes = dlg._button_spans(dlg.width)[0]
    col = dlg.abs_x + 1 + start + 1
    row = dlg.abs_y + 2
    ui.click((col, row))
    assert events == ["yes"]


def test_custom_labels():
    ui = make_ui()
    app = ui.app
    dlg = app.confirm("Delete?", yes_label="Delete", no_label="Keep")
    assert dlg.yes_label == "Delete" and dlg.no_label == "Keep"
    texts = [t for t, *_ in dlg._button_spans(dlg.width)]
    assert texts == ["[ Delete ]", "[ Keep ]"]


def test_returns_the_dialog_widget_for_inspection():
    ui = make_ui()
    app = ui.app
    dlg = app.confirm("Continue?")
    assert dlg in [e.widget for e in app._overlays]


# ── ConfirmDialog (direct, no App) ───────────────────────────────────────────


def test_width_grows_to_fit_a_long_message():
    long_message = "A" * 100
    dlg = ConfirmDialog(long_message, width=20)
    assert dlg.width >= len(long_message)


def test_button_spans_are_ordered_and_non_overlapping():
    dlg = ConfirmDialog("Continue?", width=40)
    spans = dlg._button_spans(dlg.width)
    (_, y_start, y_end, is_yes1), (_, n_start, n_end, is_yes2) = spans
    assert is_yes1 is True and is_yes2 is False
    assert y_start < y_end <= n_start < n_end


def test_tab_and_shift_tab_also_toggle():
    dlg = ConfirmDialog("Continue?", default=True)
    dlg.on_key(Key.TAB)
    assert dlg._yes is False
    dlg.on_key(Key.SHIFT_TAB)
    assert dlg._yes is True


def test_not_focused_click_outside_button_row_does_nothing():
    picked = []
    dlg = ConfirmDialog("Continue?", on_choose=picked.append)
    dlg.on_mouse_click(col=dlg.abs_x + 1, row=dlg.abs_y + 1)  # message row, not buttons
    assert picked == []
