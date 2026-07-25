"""Overlay "modern" effects: the soft drop shadow and the open/dismiss
fade+slide. The cell-level helpers are pure and tested directly; the
time-based behavior is driven through the Harness's virtual clock with
``_overlay_fx`` flipped back on (the Harness turns it off by default so the
rest of the suite reads settled frames)."""

from cozy_tui import App, Style
from cozy_tui.ansi import resolve_rgb
from cozy_tui.testing import Harness
from cozy_tui.widgets import Box, Label


def raw_app():
    return App(full=False, size="800x400", style=Style(fg="white", bg="blue"))


def _fill(app, style):
    for row in app.buffer:
        for cell in row:
            cell.style = style


# ── the gate ────────────────────────────────────────────────────────────────


def test_harness_disables_overlay_fx_by_default():
    ui = Harness(raw_app())
    assert ui.app._overlay_fx is False


def test_open_overlay_creates_an_entrance_tween_only_with_fx_on():
    app = raw_app()  # raw App defaults fx on
    box = app.open_overlay(Box(0, 0, "200x80"))
    assert app._overlays[-1].enter is not None

    app2 = raw_app()
    app2._overlay_fx = False
    app2.open_overlay(Box(0, 0, "200x80"))
    assert app2._overlays[-1].enter is None
    assert box is not None


# ── _cast_shadow ──────────────────────────────────────────────────────────────


def test_cast_shadow_darkens_the_l_below_and_right():
    app = raw_app()
    _fill(app, Style(fg="white", bg="blue"))
    app._cast_shadow(5, 5, 4, 3)  # box occupies cols 5..8, rows 5..7

    # (10, 8) is clearly in the offset strip → darkened to an rgb() tint
    assert app.buffer[8][10].style.bg.startswith("rgb(")
    # tinted toward black, so darker than the source blue
    assert resolve_rgb(app.buffer[8][10].style.raw_bg) < resolve_rgb("blue")


def test_cast_shadow_never_touches_cells_behind_the_widget():
    app = raw_app()
    _fill(app, Style(fg="white", bg="blue"))
    app._cast_shadow(5, 5, 4, 3)
    # (7, 6) sits inside the widget's own footprint: left untouched
    assert app.buffer[6][7].style.bg == "blue_bg"
    # a cell nowhere near the widget is untouched too
    assert app.buffer[20][20].style.bg == "blue_bg"


def test_shadow_has_a_soft_outer_ring():
    app = raw_app()
    _fill(app, Style(fg="white", bg="blue"))
    app._cast_shadow(5, 5, 6, 3)  # x1=11, y1=8
    near = resolve_rgb(app.buffer[8][11].style.raw_bg)  # depth 1 (touching)
    far = resolve_rgb(app.buffer[8][12].style.raw_bg)  # depth 2 (outer)
    # the near ring is darkened more than the softer far ring
    assert near[2] < far[2] < resolve_rgb("blue")[2]


# ── _fade_region ──────────────────────────────────────────────────────────────


def test_fade_region_collapses_to_the_background_at_full_amount():
    app = raw_app()
    _fill(app, Style(fg="white", bg="red"))
    app._fade_region(2, 2, 3, 2, 1.0)  # fully toward the app bg ("blue")
    blue = resolve_rgb("blue")
    assert resolve_rgb(app.buffer[2][2].style.fg) == blue
    assert resolve_rgb(app.buffer[2][2].style.raw_bg) == blue


def test_fade_region_leaves_characters_intact():
    app = raw_app()
    app.buffer[3][3].char = "Q"
    app.buffer[3][3].style = Style(fg="white", bg="red")
    app._fade_region(3, 3, 1, 1, 0.5)
    assert app.buffer[3][3].char == "Q"  # only color moves, never the glyph


# ── _apply_backdrop ───────────────────────────────────────────────────────────


def test_partial_backdrop_keeps_the_background_name_undoubled():
    app = raw_app()
    _fill(app, Style(fg="white", bg="blue"))
    app._apply_backdrop(0.5)  # partial scrim: greys fg, must not touch bg suffix
    assert app.buffer[0][0].style.bg == "blue_bg"  # not "blue_bg_bg"


# ── entrance / shadow over time ───────────────────────────────────────────────


def _open_dialog():
    app = raw_app()
    app.add(Label(0, 0, "x" * 70))
    ui = Harness(app)
    ui.app._overlay_fx = True
    box = Box(0, 0, "200x80", title="Hi", border="rounded")
    app.open_overlay(box)
    ui.compose()
    return ui, app, box


def test_entrance_tween_runs_then_settles():
    ui, app, _box = _open_dialog()
    entry = app._overlays[-1]
    assert not entry.enter.done  # just opened: still animating
    ui.advance(0.3)
    assert entry.enter.done  # past _OVERLAY_ENTER


def test_shadow_is_present_once_the_dialog_settles():
    ui, app, box = _open_dialog()
    ui.advance(0.3)
    ui.compose()
    bx, by, bw, bh = box._bounds
    # settled: the drop shadow has darkened the cell to an rgb() tint
    assert app.buffer[by + bh][bx + bw].style.bg.startswith("rgb(")


def test_shadow_scale_fades_the_whole_shadow_in():
    # scale (the overlay's entrance progress) makes the shadow deepen: a
    # half-entered overlay casts a lighter shadow than a settled one.
    app = raw_app()
    _fill(app, Style(fg="white", bg="blue"))
    app._cast_shadow(5, 5, 6, 3, scale=0.4)
    light = resolve_rgb(app.buffer[8][11].style.raw_bg)[2]

    app2 = raw_app()
    _fill(app2, Style(fg="white", bg="blue"))
    app2._cast_shadow(5, 5, 6, 3, scale=1.0)
    full = resolve_rgb(app2.buffer[8][11].style.raw_bg)[2]

    assert full < light < resolve_rgb("blue")[2]  # more entered → darker


# ── toast dismiss fade-out ────────────────────────────────────────────────────


def test_toast_dismiss_is_immediate_with_fx_off():
    app = raw_app()
    ui = Harness(app)  # fx off
    toast = app.toast("saved", duration=0)
    ui.compose()
    app._dismiss_toast(toast)
    assert toast not in app._toasts
    assert all(e.widget is not toast for e in app._overlays)


def test_toast_dismiss_defers_removal_while_fading_with_fx_on():
    app = raw_app()
    ui = Harness(app)
    ui.app._overlay_fx = True
    toast = app.toast("saved", duration=0)
    ui.compose()
    app._dismiss_toast(toast)
    entry = next(e for e in app._overlays if e.widget is toast)
    assert entry.exit is not None  # a fade-out tween was armed
    assert toast in app._toasts  # still holding its slot mid-fade
    ui.advance(0.3)  # fires the scheduled removal timer
    assert toast not in app._toasts
    assert all(e.widget is not toast for e in app._overlays)
