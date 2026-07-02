from cozy_tui import App, PromptDialog, Style
from cozy_tui.events import Key


def make_app():
    return App(full=False, size="800x300", style=Style(fg="white", bg="black"))


def type_text(widget, text):
    for ch in text:
        widget.on_key(ch)


def test_prompt_opens_as_focused_modal():
    app = make_app()
    dlg = app.prompt("Name?", "abc")
    assert isinstance(dlg, PromptDialog)
    assert app._topmost_modal() is not None
    assert app.focused is dlg
    assert dlg.text == "abc"  # prefilled


def test_enter_submits_and_closes():
    app = make_app()
    got = []
    dlg = app.prompt("Name?", on_submit=got.append)
    type_text(dlg, "hello")
    dlg.on_key(Key.ENTER)
    assert got == ["hello"]
    assert app._topmost_modal() is None  # closed after submit


def test_backspace_edits_text():
    app = make_app()
    dlg = app.prompt("Name?", "abcd")
    dlg.on_key(Key.BACKSPACE)
    dlg.on_key(Key.BACKSPACE)
    assert dlg.text == "ab"


def test_cancel_fires_on_cancel_not_on_submit():
    app = make_app()
    events = []
    app.prompt(
        "Name?",
        on_submit=lambda t: events.append(("submit", t)),
        on_cancel=lambda: events.append(("cancel",)),
    )
    app.close_overlay()  # simulates Esc / click-outside dismissal
    assert events == [("cancel",)]


def test_submit_does_not_also_fire_cancel():
    app = make_app()
    events = []
    dlg = app.prompt(
        "Name?",
        on_submit=lambda t: events.append("submit"),
        on_cancel=lambda: events.append("cancel"),
    )
    dlg.on_key(Key.ENTER)
    assert events == ["submit"]  # cancel must not fire on a successful submit
