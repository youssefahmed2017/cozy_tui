"""Shared plumbing for the search-as-you-type modal palettes: ThemePalette,
CommandPalette, and FilePicker. All three are self-contained single-widget
modals (see CLAUDE.md's "Overlays / z-layer" for why: a modal routes every
key to one focused widget, so composing an Input+ListView would need a
hand-rolled dispatcher anyway) built around the exact same query-filtered,
scroll-clamped list: type to filter `self._matches` (from `self._all`),
Up/Down/Home/End move `self._index`, Enter picks it. Everything here is
identical across all three, down to the exact key bindings -- subclasses
only supply `_matches_query(item, query)` (the filter predicate) and
`_activate_item(item)` (what picking one does); rendering (which differs
enough per widget -- icons, two-line rows, a path header, ...) stays with
each subclass.
"""

from cozy_tui.events import Key
from cozy_tui.widgets.layout.box import Box


class _SearchPaletteMixin:
    """Mixed into a ``Widget`` subclass that sets ``self._all``,
    ``self.query``, and ``self.height`` (max visible rows) in ``__init__``,
    then ``self._matches``/``self._index``/``self._scroll_off`` directly
    (mirroring what ``_refilter()`` would produce, since ``_all`` is already
    unfiltered at construction)."""

    def _matches_query(self, item, query: str) -> bool:
        """True if `item` matches the already-lowercased `query`."""
        raise NotImplementedError

    def _activate_item(self, item) -> None:
        """Called with `self._matches[self._index]` when it's picked."""
        raise NotImplementedError

    def _refilter(self) -> None:
        q = self.query.lower()
        self._matches = (
            [it for it in self._all if self._matches_query(it, q)]
            if q
            else list(self._all)
        )
        self._index = 0 if self._matches else -1
        self._scroll_off = 0

    def _clamp_scroll(self) -> None:
        if self._index < self._scroll_off:
            self._scroll_off = self._index
        elif self._index >= self._scroll_off + self.height:
            self._scroll_off = self._index - self.height + 1

    def _move(self, new_index: int) -> None:
        if not self._matches:
            return
        self._index = max(0, min(new_index, len(self._matches) - 1))
        self._clamp_scroll()

    def _activate(self) -> None:
        if 0 <= self._index < len(self._matches):
            self._activate_item(self._matches[self._index])

    def on_key(self, key) -> None:
        if key == Key.ENTER:
            self._activate()
        elif key == Key.UP:
            self._move(self._index - 1)
        elif key == Key.DOWN:
            self._move(self._index + 1)
        elif key == Key.HOME:
            self._move(0)
        elif key == Key.END:
            self._move(len(self._matches) - 1)
        elif key == Key.BACKSPACE:
            if self.query:
                self.query = self.query[:-1]
                self._refilter()
        elif isinstance(key, str) and len(key) == 1 and key.isprintable():
            self.query += key
            self._refilter()


def draw_panel_frame(canvas, x, y, w, h, border_style, fill_style) -> None:
    """Draw a rounded-border panel frame at (x, y): `w` interior columns
    wide, `h` total rows tall (border included), interior filled with
    `fill_style`. Shared by every self-contained modal dialog in this
    library (ThemePalette, CommandPalette, FilePicker, ConfirmDialog,
    PromptDialog)."""
    (tl, tr, bl, br), hc, vc = Box.BORDERS["rounded"]
    canvas.write(x, y, tl + hc * w + tr, border_style)
    for i in range(h - 2):
        canvas.write(x, y + 1 + i, vc, border_style)
        canvas.write(x + 1, y + 1 + i, " " * w, fill_style)
        canvas.write(x + w + 1, y + 1 + i, vc, border_style)
    canvas.write(x, y + h - 1, bl + hc * w + br, border_style)
