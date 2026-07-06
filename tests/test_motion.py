"""Motion primitives: easing curves, interpolation, and Tween."""

import pytest

import cozy_tui.motion as motion
from cozy_tui.motion import (Tween, ease_in, ease_in_out, ease_out,
                             ease_out_quad, lerp, lerp_color, linear)


def test_easings_hit_their_endpoints():
    for f in (linear, ease_in, ease_out, ease_in_out, ease_out_quad):
        assert abs(f(0.0)) < 1e-9
        assert abs(f(1.0) - 1.0) < 1e-9
        assert 0.0 <= f(0.5) <= 1.0


def test_ease_out_is_front_loaded():
    assert ease_out(0.5) > 0.5  # more than half-way by the midpoint


def test_lerp():
    assert lerp(0, 10, 0.5) == 5
    assert lerp(10, 20, 0.0) == 10
    assert lerp(10, 20, 1.0) == 20


def test_lerp_color_parses_and_interpolates():
    assert lerp_color((0, 0, 0), (255, 255, 255), 0.5) == "rgb(128,128,128)"
    assert lerp_color("#000000", "#ffffff", 0.0) == "rgb(0,0,0)"
    assert lerp_color("#fff", "#000", 0.0) == "rgb(255,255,255)"  # short hex expands
    assert lerp_color("rgb(0,0,0)", "rgb(10,20,30)", 1.0) == "rgb(10,20,30)"


def test_lerp_color_resolves_named_colors():
    assert lerp_color("black", "bright_white", 0.0) == "rgb(0,0,0)"
    assert lerp_color("black", "bright_white", 1.0) == "rgb(255,255,255)"


def test_lerp_color_rejects_unknown_strings():
    with pytest.raises(ValueError):
        lerp_color("chartreuse", "blue", 0.5)


def test_tween_progress_and_value(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(motion.time, "monotonic", lambda: clock[0])
    tw = Tween(0, 100, 1.0, easing=linear)
    assert tw.progress() == 0.0 and tw.value() == 0.0 and not tw.done
    clock[0] = 100.5
    assert abs(tw.value() - 50) < 1e-9
    clock[0] = 101.0
    assert tw.done and tw.value() == 100


def test_tween_zero_duration_is_immediately_done(monkeypatch):
    monkeypatch.setattr(motion.time, "monotonic", lambda: 100.0)
    tw = Tween(0, 5, 0)
    assert tw.done and tw.value() == 5


def test_tween_restart_retargets_and_resets_clock(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(motion.time, "monotonic", lambda: clock[0])
    tw = Tween(0, 10, 1.0, easing=linear)
    clock[0] = 101.0
    assert tw.done
    tw.restart(start=10, end=20)
    assert not tw.done and tw.value() == 10
