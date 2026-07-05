from cozy_tui import App, Style
from cozy_tui.widgets import AnimatedLabel, GlowAnimation


def make_app():
    return App(full=False, size="600x60", style=Style(fg="white", bg="black"))


def render(app):
    app.render_pending = True
    # mirror App.render without terminal output
    app._anim_interval = None
    app.clear()
    app._apply_docks()
    for w in app.widgets:
        w.draw(app)


def test_animated_label_requests_frames():
    app = make_app()
    anim = GlowAnimation(color_template="blue", speed=0.07)
    app.add(AnimatedLabel(0, 0, "glow", animation=anim))
    render(app)
    # The widget asked the loop to keep redrawing at its animation speed, so the
    # glow advances on its own — no app.tick_interval required.
    assert app._anim_interval == 0.07


def test_no_animation_leaves_interval_none():
    app = make_app()
    from cozy_tui.widgets import Label

    app.add(Label(0, 0, "static"))
    render(app)
    assert app._anim_interval is None


def test_request_frame_keeps_smallest_and_ignores_nonpositive():
    app = make_app()
    app._anim_interval = None
    app.request_frame(0.1)
    app.request_frame(0.05)  # faster wins
    app.request_frame(0.2)  # slower ignored
    app.request_frame(0)  # non-positive ignored
    assert app._anim_interval == 0.05


def test_effective_tick_prefers_faster_of_tick_and_anim():
    # Sanity of the min() logic the loop uses.
    app = make_app()
    app.tick_interval = 0.5
    app.request_frame(0.06)
    tick = app.tick_interval
    if app._anim_interval is not None:
        tick = app._anim_interval if tick is None else min(tick, app._anim_interval)
    assert tick == 0.06
