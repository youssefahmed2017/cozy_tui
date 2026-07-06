import re

from cozy_tui import App, Style
from cozy_tui.events import MouseMove
from cozy_tui.widgets import (AnimatedLabel, Button, GlowAnimation,
                              LevitateAnimation, RainbowAnimation)


def make_app(**kw):
    return App(full=False, size="600x200", style=Style(fg="white", bg="black"), **kw)


# ── RainbowAnimation ──────────────────────────────────────────────────────────


def test_rainbow_colors_every_char_with_truecolor():
    anim = RainbowAnimation(spread=30)
    cells = list(anim.cells("abc", Style(fg="white")))
    assert len(cells) == 3
    for i, (dx, dy, ch, style) in enumerate(cells):
        assert (dx, dy, ch) == (i, 0, "abc"[i])
        assert re.fullmatch(r"rgb\(\d+,\d+,\d+\)", style.fg)


def test_rainbow_adjacent_chars_differ_in_hue():
    anim = RainbowAnimation(spread=60)
    cells = list(anim.cells("ab", Style()))
    assert cells[0][3].fg != cells[1][3].fg  # spread apart on the wheel


def test_rainbow_preserves_background():
    anim = RainbowAnimation()
    ((_, _, _, style),) = list(anim.cells("x", Style(bg="blue")))
    assert style.bg == "blue_bg"


# ── LevitateAnimation ─────────────────────────────────────────────────────────


def test_levitate_char_offsets_within_range():
    anim = LevitateAnimation(mode="char", amplitude=4)
    assert anim.vertical_span == 8
    for dx, dy, ch, style in anim.cells("hello", Style()):
        assert 0 <= dy <= 8


def test_levitate_word_moves_all_chars_together():
    anim = LevitateAnimation(mode="word", amplitude=4)
    offsets = {dy for _, dy, _, _ in anim.cells("hello", Style())}
    assert len(offsets) == 1  # whole word shares one offset


def test_levitate_char_can_stagger():
    # Over the phase, char mode produces more than one distinct offset.
    anim = LevitateAnimation(mode="char", amplitude=6, phase=1.0)
    seen = set()
    for _ in range(40):
        seen |= {dy for _, dy, _, _ in anim.cells("abcdefgh", Style())}
        anim._start -= 0.03  # advance frames
    assert len(seen) > 1


def test_levitate_rejects_bad_mode():
    import pytest

    with pytest.raises(ValueError):
        LevitateAnimation(mode="spin")


def test_levitate_leaves_color_alone():
    anim = LevitateAnimation()
    base = Style(fg="cyan", bg="black")
    ((_, _, _, style),) = list(anim.cells("z", base))
    assert style is base  # untouched style passed straight through


# ── AnimatedLabel integration ─────────────────────────────────────────────────


def test_animated_label_height_accounts_for_levitation():
    lbl = AnimatedLabel(0, 0, "x", animation=LevitateAnimation(amplitude=3))
    assert lbl.natural_height(10) == 1 + 6


def test_animated_label_drives_frame_loop():
    app = make_app()
    app.add(AnimatedLabel(0, 0, "hi", animation=RainbowAnimation(speed=0.04)))
    app.snapshot()
    assert app._anim_interval == 0.04


def test_glow_still_works_via_cells():
    anim = GlowAnimation(color_template="orange")
    cells = list(anim.cells("hi", Style()))
    assert len(cells) == 2
    assert all(c[3].fg.startswith("rgb(") for c in cells)


# ── Button hover / enter-leave / animation ────────────────────────────────────


def test_button_hover_enter_and_leave():
    app = make_app()
    b1 = Button(0, 0, "One")
    b2 = Button(0, 2, "Two")
    b2.mouse_moves = True  # opt into hover (registering on_enter does this for b1)
    entered, left = [], []
    b1.on_enter(lambda w: entered.append("b1"))  # also enables b1.mouse_moves
    b1.on_leave(lambda w: left.append("b1"))
    app.add(b1)
    app.add(b2)

    app._dispatch_mouse(MouseMove(1, 0))  # over b1
    assert b1._hovered and entered == ["b1"]
    app._dispatch_mouse(MouseMove(1, 2))  # move to b2 -> b1 leaves
    assert not b1._hovered and left == ["b1"]
    assert b2._hovered


def test_button_animation_requests_frames_when_focused():
    app = make_app()
    b = Button(0, 0, "Go", animation=RainbowAnimation(speed=0.05))
    app.add(b)
    app.focus(b)
    app.snapshot()
    assert app._anim_interval == 0.05


def test_button_animation_idle_does_not_animate():
    app = make_app()
    b = Button(0, 0, "Go", animation=RainbowAnimation(speed=0.05))
    app.add(b)  # not focused, not hovered
    app.snapshot()
    assert app._anim_interval is None


def test_button_active_effect_tints_toward_background():
    app = make_app()  # screen bg is black
    b = Button(0, 0, "OK", style=Style(fg="white", bg="red"))
    app.add(b)
    app._compose()
    idle_bg = app.buffer[0][0].style.bg

    b.on_mouse_click()  # activate → tint toward black
    app._compose()
    active_bg = app.buffer[0][0].style.bg
    assert b._active
    assert active_bg.startswith("rgb(")  # tinted, not a plain named color
    assert active_bg != idle_bg
    # The button keeps the loop alive so the effect can revert on its own.
    assert app._anim_interval == b.active_effect_duration


def test_button_active_effect_reverts_after_duration():
    app = make_app()
    b = Button(0, 0, "OK", style=Style(fg="white", bg="red"))
    app.add(b)
    b.on_mouse_click()
    b._active_time -= 1.0  # pretend the duration has elapsed
    app._compose()
    assert not b._active
    assert app.buffer[0][0].style.bg == "red_bg"  # back to normal


def test_button_zero_duration_disables_active_effect():
    b = Button(0, 0, "OK", active_effect_duration=0)
    b.on_mouse_click()
    assert not b._active


def test_button_bg_fades_between_states_on_focus(monkeypatch):
    import cozy_tui.motion as motion

    app = make_app()  # screen bg black
    b = Button(0, 0, "OK", style=Style(fg="white", bg="blue"))
    app.add(b)
    app._compose()  # first draw snaps to idle
    assert app.buffer[0][0].style.bg == "blue_bg"  # idle: exact named colour

    clock = [100.0]
    monkeypatch.setattr(motion.time, "monotonic", lambda: clock[0])
    app.focus(b)
    app._compose()  # starts the fade tween at t=100.0
    clock[0] = 100.05  # mid-fade
    app._compose()
    assert app.buffer[0][0].style.bg.startswith("rgb(")  # interpolating in RGB

    clock[0] = 100.2  # settled
    app._compose()
    assert app.buffer[0][0].style.bg == "white_bg"  # focused: exact named again
