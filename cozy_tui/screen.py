"""Screens: named, swappable sets of top-level widgets.

A screen is just a named widget list — a menu, a game, a game-over panel — and
switching between them swaps which list the app draws::

    menu = app.screen("menu")
    menu.add(Label(2, 2, "PAUSED"))
    menu.dock(footer, "bottom")

    game = app.screen("game")
    game.add(board)

    app.show("menu")

There is no ``Screen`` subclass to write, no lifecycle to learn, and no routing
table. ``screen.add``/``screen.dock``/``screen.focus`` are the same three calls
you already make on ``App`` — a screen *is* what ``app.widgets`` holds, given a
name so there can be more than one.

**Screens keep their widgets.** Switching away and back leaves a half-typed
form, a scroll position, and the focused widget exactly as they were; nothing is
rebuilt. That's the reason a screen is a list rather than a builder function —
a `build()` called on every switch would be simpler to implement and would
silently discard state the user cares about.

Not using screens costs nothing: ``app.widgets`` behaves exactly as it always
has until :meth:`App.screen` is called for the first time.
"""

from __future__ import annotations

from cozy_tui._dock import SIDES

__all__ = ["Screen"]


class Screen:
    """One named set of top-level widgets. Create via :meth:`App.screen`."""

    def __init__(self, app, name: str):
        self.app = app
        self.name = name
        self.widgets: list = []
        # Restored on the way back in. Remembered rather than recomputed so
        # returning to a screen resumes where the user left off instead of
        # jumping to its first field.
        self.focused = None
        self._show_handler = None
        self._hide_handler = None
        # Key bindings scoped to this screen; consulted before the app-wide
        # ones while it's showing (see App._dispatch_input).
        self._key_handlers: dict = {}

    # ── building ─────────────────────────────────────────────────────────────

    def add(self, widget):
        """Add a top-level widget to this screen. Returns it."""
        self.widgets.append(widget)
        if self.is_current:
            self.app._ensure_motion_mode()
        return widget

    def dock(self, widget, side, margin=0):
        """Dock a widget against a screen edge — the same call as
        :meth:`App.dock`, scoped to this screen. Returns the widget."""
        if side not in SIDES:
            raise ValueError(f"dock side must be one of {SIDES}, got {side!r}")
        widget._dock = (side, margin)
        if widget not in self.widgets:
            self.add(widget)
        return widget

    def remove(self, widget):
        """Remove a widget from this screen (anywhere in its tree). Returns it,
        or ``None``. Delegates to :meth:`App.remove` while this screen is
        showing, so focus is handled the same way."""
        if self.is_current:
            return self.app.remove(widget)
        if widget in self.widgets:
            self.widgets.remove(widget)
            widget.parent = None
            if self.focused is not None and self.app._subtree_contains(
                widget, self.focused
            ):
                self.focused = None
            return widget
        owner = self.app._owner_of(widget, self.widgets)
        return owner.remove(widget) if owner is not None else None

    def focus(self, widget):
        """Focus `widget` on this screen — immediately if it's showing, and on
        the next :meth:`App.show` otherwise."""
        if self.is_current:
            self.app.focus(widget)
        else:
            self.focused = widget
        return widget

    # ── input ────────────────────────────────────────────────────────────────

    def on_key(self, key, handler, *, description=None, section=None):
        """Register a key handler that only applies while this screen is
        showing, and which **takes precedence** over the app-wide binding for
        the same key.

        This is what lets Esc mean "back" on one screen and "quit" on another
        without a dispatcher in the middle checking which screen is current.
        Returns the screen, so calls chain.
        """
        self._key_handlers[key] = handler
        if description is not None:
            self.app._bindings[key] = (description, section)
            self.app._bindings_version += 1
        return self

    # ── lifecycle ────────────────────────────────────────────────────────────

    def on_show(self, func):
        """Register a callback fired each time this screen is switched *to*,
        after its widgets are live. Receives the screen."""
        self._show_handler = func
        return self

    def on_hide(self, func):
        """Register a callback fired each time this screen is switched *away
        from*, before the new one is installed. Receives the screen."""
        self._hide_handler = func
        return self

    @property
    def is_current(self) -> bool:
        return self.app.current_screen is self

    def __repr__(self) -> str:
        live = " (showing)" if self.is_current else ""
        return f"<Screen {self.name!r} {len(self.widgets)} widgets{live}>"
