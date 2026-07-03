import cozy_tui.widgets.display.hyperlink as hl_mod
from cozy_tui import App, Hyperlink, Style
from cozy_tui.events import Key


def make_app():
    return App(full=False, size="800x120", style=Style(fg="white", bg="black"))


def link_and_app(monkeypatch_opened):
    app = make_app()
    link = Hyperlink(2, 1, "Click me", "https://example.com")
    # Redirect the real browser call into a list so tests never launch anything.
    link._open = lambda: monkeypatch_opened.append(link.link)
    app.add(link)
    app.focus(link)
    return app, link


def test_focusable_and_in_focus_order():
    app = make_app()
    link = Hyperlink(0, 0, "x", "https://x")
    app.add(link)
    assert link.focusable is True
    assert app._collect_focusables() == [link]


def test_contains_hit_box():
    link = Hyperlink(2, 1, "Click me", "https://example.com")  # width 8: cols 2..9
    assert link.contains(2, 1) is True
    assert link.contains(9, 1) is True
    assert link.contains(10, 1) is False  # just past the end
    assert link.contains(5, 2) is False   # wrong row


def test_enter_and_space_open_when_focused():
    opened = []
    _, link = link_and_app(opened)
    link.on_key(Key.ENTER)
    link.on_key(" ")
    assert opened == ["https://example.com", "https://example.com"]


def test_mouse_click_opens():
    opened = []
    _, link = link_and_app(opened)
    link.on_mouse_click(3, 1)
    assert opened == ["https://example.com"]


def test_draw_renders_text_without_blocking():
    app, link = link_and_app([])
    app.clear()
    for w in app.widgets:
        w.draw(app)
    row = "".join(c.char for c in app.buffer[1]).strip()
    assert row == "Click me"


def test_real_open_calls_webbrowser(monkeypatch):
    calls = []
    monkeypatch.setattr(hl_mod.webbrowser, "open", lambda url: calls.append(url))
    Hyperlink(0, 0, "t", "https://real").on_key(Key.ENTER)
    assert calls == ["https://real"]
