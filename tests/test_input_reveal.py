"""Input's masked-field reveal ("eye") toggle: the icon's hit-zone and
sizing, Ctrl+R, blocking copy/cut while hidden, and auto-hide on blur."""

from cozy_tui import App, Style
from cozy_tui.events import Key
from cozy_tui.widgets import Button, Input
from cozy_tui.widgets.input import _input_keys as keys_mod


def make_app():
    return App(full=False, size="300x100", style=Style(fg="white", bg="black"))


def make_masked(value="hunter2secret", **kw):
    inp = Input(2, 1, 20, masked=True, **kw)
    inp.value = value
    inp.cursor_pos = len(value)
    return inp


def icon_col(inp) -> int:
    return inp.abs_x + inp.width + inp._ICON_GAP


# ── _display_value ────────────────────────────────────────────────────────────


def test_display_value_is_masked_by_default():
    inp = make_masked()
    assert inp._display_value == "*" * len("hunter2secret")


def test_display_value_shows_real_text_when_revealed():
    inp = make_masked()
    inp._reveal_masked = True
    assert inp._display_value == "hunter2secret"


# ── sizing ────────────────────────────────────────────────────────────────────


def test_natural_width_grows_by_icon_reservation_when_masked():
    inp = make_masked()
    assert inp.natural_width(1) == 20 + inp._ICON_GAP + inp._ICON_WIDTH


def test_natural_width_unchanged_for_unmasked_input():
    inp = Input(2, 1, 20)
    assert inp.natural_width(1) == 20


def test_natural_width_unchanged_when_multiline():
    inp = make_masked(multiline=True)
    assert inp.natural_width(1) == 20


def test_natural_width_unchanged_when_clip_width_set():
    inp = make_masked()
    inp._clip_width = 10
    assert inp.natural_width(1) == 20


def test_contains_covers_the_icon_zone():
    app = make_app()
    inp = make_masked()
    app.add(inp)
    app.snapshot()
    assert inp.contains(icon_col(inp), inp.abs_y)
    assert inp.contains(icon_col(inp) + 1, inp.abs_y)
    assert not inp.contains(icon_col(inp) + inp._ICON_WIDTH, inp.abs_y)


# ── click ─────────────────────────────────────────────────────────────────────


def test_clicking_the_icon_toggles_reveal_without_moving_cursor():
    app = make_app()
    inp = make_masked()
    app.add(inp)
    app.focus(inp)
    app.snapshot()
    inp.cursor_pos = 3

    inp.on_mouse_click(icon_col(inp), inp.abs_y)
    assert inp._reveal_masked is True
    assert inp.cursor_pos == 3  # unchanged
    assert inp._sel_anchor is None  # no selection started

    inp.on_mouse_click(icon_col(inp), inp.abs_y)
    assert inp._reveal_masked is False


def test_clicking_the_real_text_area_still_works_normally():
    app = make_app()
    inp = make_masked()
    app.add(inp)
    app.snapshot()
    inp.on_mouse_click(inp.abs_x + 3, inp.abs_y)
    assert inp.cursor_pos == 3
    assert inp._reveal_masked is False


def test_icon_has_no_hit_zone_when_input_is_not_masked():
    app = make_app()
    inp = Input(2, 1, 20)
    inp.value = "plain text"
    app.add(inp)
    app.snapshot()
    # clicking past the declared width does nothing special (no icon exists)
    inp.on_mouse_click(inp.abs_x + 20, inp.abs_y)
    assert not hasattr(inp, "_reveal_masked") or inp._reveal_masked is False


# ── keyboard ──────────────────────────────────────────────────────────────────


def test_ctrl_r_toggles_reveal():
    inp = make_masked()
    inp.on_key(Key.CTRL_R)
    assert inp._reveal_masked is True
    inp.on_key(Key.CTRL_R)
    assert inp._reveal_masked is False


def test_ctrl_r_is_a_noop_on_unmasked_input():
    inp = Input(2, 1, 20)
    inp.value = "plain"
    inp.on_key(Key.CTRL_R)
    assert inp._reveal_masked is False


# ── copy / cut blocked while hidden ───────────────────────────────────────────


def test_ctrl_c_copies_nothing_while_hidden(monkeypatch):
    copied = []
    monkeypatch.setattr(keys_mod, "_clipboard_set", copied.append)
    inp = make_masked()
    inp.on_key(Key.CTRL_A)
    inp.on_key(Key.CTRL_C)
    assert copied == []


def test_ctrl_c_copies_the_real_value_once_revealed(monkeypatch):
    copied = []
    monkeypatch.setattr(keys_mod, "_clipboard_set", copied.append)
    inp = make_masked()
    inp._reveal_masked = True
    inp.on_key(Key.CTRL_A)
    inp.on_key(Key.CTRL_C)
    assert copied == ["hunter2secret"]


def test_ctrl_x_cuts_nothing_while_hidden(monkeypatch):
    copied = []
    monkeypatch.setattr(keys_mod, "_clipboard_set", copied.append)
    inp = make_masked()
    original = inp.value
    inp.on_key(Key.CTRL_A)
    inp.on_key(Key.CTRL_X)
    assert copied == []
    assert inp.value == original  # nothing was cut either


def test_ctrl_c_unaffected_for_unmasked_input(monkeypatch):
    copied = []
    monkeypatch.setattr(keys_mod, "_clipboard_set", copied.append)
    inp = Input(2, 1, 20)
    inp.value = "plain text"
    inp.on_key(Key.CTRL_A)
    inp.on_key(Key.CTRL_C)
    assert copied == ["plain text"]


# ── auto-hide on blur ─────────────────────────────────────────────────────────


def test_reveal_resets_when_focus_moves_away():
    app = make_app()
    inp = make_masked()
    btn = Button(2, 5, "Other")
    app.add(inp)
    app.add(btn)
    app.focus(inp)
    inp._reveal_masked = True
    app.snapshot()
    assert inp._reveal_masked is True  # still focused -- unchanged

    app.focus(btn)
    app.snapshot()  # draw() notices the blur on this pass
    assert inp._reveal_masked is False


def test_reveal_stays_true_while_still_focused_across_redraws():
    app = make_app()
    inp = make_masked()
    app.add(inp)
    app.focus(inp)
    inp._reveal_masked = True
    app.snapshot()
    app.snapshot()
    assert inp._reveal_masked is True
