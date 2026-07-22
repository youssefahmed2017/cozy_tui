"""Tests for the reactive State system (cozy_tui/state.py) and the widget
properties wired to it via Widget.bind()."""

import gc

from cozy_tui import App, State, Style
from cozy_tui.testing import Harness
from cozy_tui.widgets import Box, Button, Checkbox, Hyperlink, Label, ProgressBar, Text


def make_ui():
    return Harness(App(full=False, size="600x100", style=Style(fg="white", bg="black")))


def row_text(app, r):
    return "".join(c.char for c in app.buffer[r]).rstrip()


# ── State core ───────────────────────────────────────────────────────────────


def test_value_round_trips():
    s = State("hello")
    assert s.value == "hello"


def test_assigning_value_notifies():
    s = State("a")
    seen = []
    s.subscribe(seen.append)
    s.value = "b"
    assert seen == ["b"]
    assert s.value == "b"


def test_set_is_equivalent_to_assignment_and_returns_the_value():
    s = State(1)
    seen = []
    s.subscribe(seen.append)
    assert s.set(2) == 2
    assert seen == [2]


def test_setting_an_equal_value_does_not_notify():
    s = State("same")
    seen = []
    s.subscribe(seen.append)
    s.value = "same"
    assert seen == []  # no pointless fan-out / repaint


def test_update_derives_from_the_current_value():
    count = State(41)
    assert count.update(lambda n: n + 1) == 42
    assert count.value == 42


def test_unsubscribe_stops_delivery():
    s = State(0)
    seen = []
    cb = s.subscribe(seen.append)  # subscribe returns the callback
    s.value = 1
    s.unsubscribe(cb)
    s.value = 2
    assert seen == [1]


def test_unsubscribing_an_unknown_callback_is_a_no_op():
    State(0).unsubscribe(lambda _v: None)  # must not raise


def test_all_subscribers_are_notified_in_order():
    s = State(0)
    order = []
    s.subscribe(lambda v: order.append(("first", v)))
    s.subscribe(lambda v: order.append(("second", v)))
    s.value = 9
    assert order == [("first", 9), ("second", 9)]


def test_subscribing_during_a_notification_does_not_crash_or_fire_early():
    # The listener list is snapshotted per notification, so mutating it from
    # inside a callback is safe and only affects the *next* change.
    s = State(0)
    late = []
    s.subscribe(lambda _v: s.subscribe(late.append))
    s.value = 1
    assert late == []
    s.value = 2
    assert late == [2]


def test_value_with_a_broken_eq_is_treated_as_changed():
    class Weird:
        def __eq__(self, other):
            raise RuntimeError("no comparisons here")

    s = State(Weird())
    seen = []
    s.subscribe(seen.append)
    s.value = Weird()
    assert len(seen) == 1  # over-notified rather than swallowing the exception


def test_repr_and_str():
    assert str(State("Ready")) == "Ready"
    assert "Ready" in repr(State("Ready"))
    assert "status" in repr(State("Ready", name="status"))


# ── binding ──────────────────────────────────────────────────────────────────


def test_bind_sets_the_attribute_immediately_and_on_change():
    s = State("one")

    class Target:
        pass

    t = Target()
    assert s.bind(t, "label") == "one"
    assert t.label == "one"
    s.value = "two"
    assert t.label == "two"


def test_bind_is_weak_in_the_target():
    s = State("x")

    class Target:
        pass

    t = Target()
    s.bind(t, "label")
    assert len(s._subs) == 1
    del t
    gc.collect()
    s.value = "y"  # prunes the dead subscription rather than raising
    assert s._subs == []


# ── widgets: plain values still behave exactly as before ─────────────────────


def test_plain_string_needs_no_state_and_creates_no_subscription():
    label = Label(0, 0, "plain")
    assert label.text == "plain"
    label.text = "reassigned"  # still an ordinary attribute
    assert label.text == "reassigned"


# ── widgets: reactive properties ─────────────────────────────────────────────


def test_label_text_follows_its_state_on_screen():
    ui = make_ui()
    app = ui.app
    name = State("Text")
    app.add(Label(0, 0, name))
    ui.compose()
    assert row_text(app, 0) == "Text"

    name.value = "HELLO"
    ui.compose()
    assert row_text(app, 0) == "HELLO"


def test_shrinking_text_leaves_no_stale_characters():
    # The buffer is cleared each frame and the diff picks up the blanked cells,
    # so a shorter value must not leave the old tail behind.
    ui = make_ui()
    app = ui.app
    name = State("LONG VALUE HERE")
    app.add(Label(0, 0, name))
    ui.compose()
    name.value = "HI"
    ui.compose()
    assert row_text(app, 0) == "HI"


def test_one_state_drives_several_widgets():
    ui = make_ui()
    app = ui.app
    title = State("Downloads")
    label = Label(0, 0, title)
    box = Box(0, 2, "200x40", title=title)
    app.add(label)
    app.add(box)

    title.value = "Downloads (3)"
    assert label.text == "Downloads (3)"
    assert box.title == "Downloads (3)"
    ui.compose()
    assert "Downloads (3)" in row_text(app, 2)  # the box's top border row


def test_label_natural_width_tracks_the_state():
    name = State("ab")
    label = Label(0, 0, name)
    assert label.natural_width(App.SCALE) == 2
    name.value = "abcdef"
    assert label.natural_width(App.SCALE) == 6


def test_box_text_and_title_are_independently_bindable():
    text = State("body")
    title = State("head")
    box = Box(0, 0, "200x40", text=text, title=title)
    text.value = "new body"
    assert (box.text, box.title) == ("new body", "head")


def test_button_text_is_reactive():
    caption = State("Start")
    button = Button(0, 0, caption)
    caption.value = "Stop"
    assert button.text == "Stop"


def test_checkbox_text_is_reactive():
    caption = State("Enable")
    box = Checkbox(0, 0, caption)
    caption.value = "Disable"
    assert box.text == "Disable"


def test_hyperlink_text_and_link_are_reactive():
    text, link = State("Docs"), State("https://example.com")
    widget = Hyperlink(0, 0, text, link)
    text.value = "Home"
    link.value = "https://example.org"
    assert (widget.text, widget.link) == ("Home", "https://example.org")


def test_text_widget_rewraps_when_its_state_changes():
    # Text stores content behind a property whose setter drops the wrap cache;
    # binding must go through that setter, not around it.
    body = State("short")
    widget = Text(0, 0, body, size="10x5")
    assert widget._get_lines() == ["short"]
    body.value = "a much longer line that has to wrap"
    assert len(widget._get_lines()) > 1


def test_progress_bar_clamps_values_arriving_from_a_state():
    amount = State(10)
    bar = ProgressBar(0, 0, progress=amount, minimum=0, maximum=100)
    assert bar.get() == 10
    amount.value = 250
    assert bar.get() == 100  # clamped by the property setter, as a manual set() is
    amount.value = -5
    assert bar.get() == 0


def test_progress_bar_change_handler_fires_for_state_driven_updates():
    seen = []
    amount = State(0)
    bar = ProgressBar(0, 0, progress=amount)
    bar.on_change(seen.append)
    amount.value = 50
    assert seen == [50]


def test_progress_property_matches_get():
    bar = ProgressBar(0, 0, progress=25)
    assert bar.progress == 25
    bar.progress = 60
    assert bar.get() == 60


def test_dropped_widget_does_not_keep_its_subscription_alive():
    # An app that spawns and discards widgets continuously must not accumulate
    # listeners on a long-lived State.
    shared = State("v")
    for _ in range(50):
        Label(0, 0, shared)
    gc.collect()
    shared.value = "w"
    assert shared._subs == []


def test_a_bound_method_subscription_does_not_pin_its_owner():
    # The natural thing to write -- s.subscribe(self.refresh, owner=self) --
    # would otherwise defeat the weak `owner` entirely, because a bound method
    # holds its instance strongly.
    s = State(0)

    class Listener:
        def __init__(self):
            self.seen = []

        def refresh(self, value):
            self.seen.append(value)

    listener = Listener()
    s.subscribe(listener.refresh, owner=listener)
    s.value = 1
    assert listener.seen == [1]

    del listener
    gc.collect()
    s.value = 2  # must not raise, and must prune the dead subscription
    assert s._subs == []


def test_a_bound_method_subscription_can_be_unsubscribed():
    s = State(0)

    class Listener:
        def __init__(self):
            self.seen = []

        def refresh(self, value):
            self.seen.append(value)

    listener = Listener()
    s.subscribe(listener.refresh, owner=listener)
    s.unsubscribe(listener.refresh)  # a *different* bound-method object
    s.value = 1
    assert listener.seen == []
