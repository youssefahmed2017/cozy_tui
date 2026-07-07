"""Internal: the debug-log overlay toggled by F12 when `App(debug=True)`.

Not part of the public API. Docked top-left corner, a quarter of the screen —
a Chrome-DevTools-style inspector panel, not a centered dialog.
"""

from cozy_tui.widgets import Box, Label, ScrollView


class _LiveLog(ScrollView):
    """Self-updating ScrollView showing App._debug_log. Only rebuilds its rows
    when `App._debug_seq` has moved since it last drew, so `app.debug(...)`
    calls — which may happen far more often than the pane is ever open — do
    no work of their own; the sync cost lands on the pane's own `draw()`."""

    def __init__(self, app, x, y, size):
        super().__init__(x, y, size, autoscroll=True)
        self._app = app
        self._synced_seq = -1

    def draw(self, canvas):
        if self._synced_seq != self._app._debug_seq:
            self._synced_seq = self._app._debug_seq
            self.clear()
            for i, line in enumerate(self._app._debug_log):
                self.add(Label(0, i, line))
        super().draw(canvas)


class DebugPane(Box):
    def __init__(self, app, x, y, size):
        super().__init__(x, y, size, title="Debug Log", border="rounded")
        # Box grows to fit a non-lapping child's right edge, so a ScrollView
        # sized to the box's *own* full width (starting at x=1, inside the
        # border) would push the box one cell wider every time. Inset by one
        # scale unit (= one cell) on both axes so it fits inside the border
        # without growing it.
        scale = app.SCALE
        w_px, h_px = (int(v) for v in size.split("x"))
        inner_size = f"{max(scale, w_px - scale)}x{max(scale, h_px - scale)}"
        self.add(_LiveLog(app, 1, 1, inner_size))
