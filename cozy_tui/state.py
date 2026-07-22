"""Reactive values: a ``State`` holds a value, and anything bound to it updates
when that value changes.

::

    from cozy_tui.state import State

    title = State("Downloads")

    app.add(Label(2, 1, title))
    app.add(Box(2, 3, "400x100", title=title))

    title.value = "Downloads (3)"   # both the label and the box title update

The design is deliberately **explicit and un-magical**: a plain ``str`` never
becomes reactive on its own, and there is no dependency tracking, no proxying,
and no compile step. ``State`` is an observable box; a widget that accepts one
resolves it to a plain value up front and re-assigns that plain attribute
whenever the box changes. Widgets keep storing plain values, so every existing
``self.text``/``self.title`` read (and every widget that was never taught about
``State``) works exactly as before.

**Assignment is the API.** ``s.value = x`` notifies; :meth:`State.set` is the
same thing as a callable, for use in a lambda or as a ready-made callback.

Notification is synchronous — by the time ``s.value = x`` returns, every bound
widget attribute has already been updated. There is no scheduler and no
coalescing: the *repaint* is the render loop's ordinary next frame, which
happens after key/mouse dispatch, after a timer fires, and after a worker's
``on_result`` — i.e. after all four places user code normally runs. Setting a
``State`` directly from a background thread updates the attributes but will not
schedule a frame; hand the value back through ``run_worker(on_result=...)``
instead, the same rule that already applies to touching widgets from a thread.
"""

from __future__ import annotations

import weakref
from typing import Any, Callable, Generic, TypeVar

__all__ = ["State"]

T = TypeVar("T")


def _differs(old: Any, new: Any) -> bool:
    """True if ``new`` should count as a change from ``old``.

    Equal values are dropped so that re-setting the same value doesn't fan out
    a pointless notification (and so a listener that writes back its own value
    terminates instead of recursing). Anything whose ``__eq__`` raises or
    returns a non-bool (an array-like, say) is treated as changed — an
    over-notification is harmless, a swallowed exception in a setter is not.
    """
    if old is new:
        return False
    try:
        return not bool(old == new)
    except Exception:
        return True


class State(Generic[T]):
    """An observable value.

    :param value: the initial value.
    :param name: optional label, shown in ``repr()`` — handy when several
        states are in flight while debugging.
    """

    __slots__ = ("_value", "_name", "_subs", "__weakref__")

    def __init__(self, value: T = None, *, name: str = ""):
        self._value = value
        self._name = name
        # [(callback, owner_ref_or_None)]. A list, not a set: callbacks are
        # frequently un-hashable-in-spirit closures, and subscription order is
        # worth keeping stable so updates land in a predictable order.
        self._subs: list[tuple[Callable[[T], Any], Any]] = []

    # ── value ────────────────────────────────────────────────────────────────

    @property
    def value(self) -> T:
        return self._value

    @value.setter
    def value(self, new: T) -> None:
        self.set(new)

    def set(self, new: T) -> T:
        """Set the value and notify listeners if it actually changed. Returns
        the new value. Identical to assigning :attr:`value`; exists so a state
        can be updated from a lambda or passed straight to a callback slot
        (``button.on_click(lambda _b: flag.set(True))``)."""
        old = self._value
        self._value = new
        if _differs(old, new):
            self._notify()
        return new

    def update(self, func: Callable[[T], T]) -> T:
        """Set the value to ``func(current)`` — ``count.update(lambda n: n + 1)``.
        Saves a read-modify-write round trip when the new value depends on the
        old one."""
        return self.set(func(self._value))

    # ── subscription ─────────────────────────────────────────────────────────

    def subscribe(self, callback: Callable[[T], Any], *, owner: Any = None):
        """Call ``callback(new_value)`` whenever the value changes. Returns the
        callback, so a decorator or an inline lambda can be kept for
        :meth:`unsubscribe`.

        ``owner`` makes the subscription **weak**: it is dropped automatically
        once ``owner`` is garbage collected. Widget bindings use this so a
        discarded widget doesn't keep itself (and its whole parent chain) alive
        through a long-lived state — the case that turns a reactive system into
        a leak in an app that spawns and drops widgets continuously.

        Passing ``owner``'s own bound method (``s.subscribe(self.refresh,
        owner=self)``) is the natural thing to write and would otherwise defeat
        the whole point: a bound method holds its instance *strongly*, so the
        weak ``owner`` reference could never die. That case is detected and
        stored as a :class:`weakref.WeakMethod` instead.
        """
        entry = callback
        if owner is not None and getattr(callback, "__self__", None) is owner:
            entry = weakref.WeakMethod(callback)
        self._subs.append((entry, weakref.ref(owner) if owner is not None else None))
        return callback

    def unsubscribe(self, callback: Callable[[T], Any]) -> None:
        """Remove a previously subscribed callback. Silently ignores one that
        isn't subscribed."""

        def matches(stored):
            if isinstance(stored, weakref.WeakMethod):
                # Bound methods are recreated per attribute access, so identity
                # never holds; `==` compares (instance, function) as intended.
                return stored() == callback
            return stored is callback

        self._subs = [entry for entry in self._subs if not matches(entry[0])]

    def bind(self, obj: Any, attr: str) -> T:
        """Keep ``obj.attr`` equal to this state's value, now and on every
        change, and return the current value.

        The subscription is weak in ``obj``. Assignment goes through ordinary
        ``setattr``, so a target that exposes the attribute as a property (and
        re-wraps/re-clamps in its setter, as :class:`~cozy_tui.widgets.Text` and
        :class:`~cozy_tui.widgets.ProgressBar` do) reacts exactly as it would to
        a hand-written assignment.
        """
        setattr(obj, attr, self._value)
        ref = weakref.ref(obj)

        def _apply(new, ref=ref, attr=attr):
            target = ref()
            if target is not None:  # else: dead, pruned by _notify below
                setattr(target, attr, new)

        self.subscribe(_apply, owner=obj)
        return self._value

    def _notify(self) -> None:
        live = []
        for entry in self._subs:  # snapshot: a callback may sub/unsub mid-flight
            stored, owner_ref = entry
            if owner_ref is not None and owner_ref() is None:
                continue  # owner is gone; drop the subscription
            if isinstance(stored, weakref.WeakMethod) and stored() is None:
                continue  # the method's instance is gone
            live.append(entry)
        if len(live) != len(self._subs):
            self._subs = live
        for stored, _owner in live:
            callback = stored() if isinstance(stored, weakref.WeakMethod) else stored
            if callback is not None:
                callback(self._value)

    # ── plumbing ─────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        label = f" {self._name}" if self._name else ""
        return f"<State{label} {self._value!r}>"

    def __str__(self) -> str:
        # A State that reaches a plain string context should read as its value
        # rather than as an object address — an f-string in a toast or a debug
        # line is the common case, and "<State 'Ready'>" there is never wanted.
        return str(self._value)
