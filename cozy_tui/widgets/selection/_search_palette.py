"""Shared plumbing for the search-as-you-type palettes: the modal
ThemePalette, CommandPalette, and FilePicker (see CLAUDE.md's "Overlays /
z-layer" for why each is a single self-contained widget rather than a
composed Input+ListView: a modal routes every key to one focused widget, so
composing two would need a hand-rolled dispatcher anyway), and the inline,
non-modal SearchBar. All four are built around the exact same
query-filtered, scroll-clamped list: type to filter `self._matches` (from
`self._all`), Up/Down/Home/End move `self._index`, Enter picks it.
Everything here is identical across all four, down to the exact key
bindings -- subclasses only supply `_matches_query(item, query)` (the
substring filter predicate) and `_activate_item(item)` (what picking one
does); rendering (which differs enough per widget -- icons, two-line rows, a
path header, ...) stays with each subclass.
"""

from cozy_tui.events import Key
from cozy_tui.widgets.layout.box import Box


def fuzzy_score(text: str, query: str) -> float | None:
    """`None` if `query`'s characters don't all appear, in order, in `text`
    (case-insensitive) -- not a match at all. Otherwise a score where higher
    is a better match: an exact substring always outranks a loose
    subsequence match (and an earlier substring beats a later one); among
    subsequence matches, consecutive matched characters and shorter gaps
    between them score progressively higher than a scattered match."""
    text_l, query_l = text.lower(), query.lower()
    if not query_l:
        return 0.0
    exact = text_l.find(query_l)
    if exact != -1:
        return 1000.0 - exact
    score = 0.0
    pos = 0
    streak = 0
    for ch in query_l:
        found = text_l.find(ch, pos)
        if found == -1:
            return None
        if found == pos:
            streak += 1
            score += 2 + streak  # consecutive matches compound
        else:
            streak = 0
            score += max(0.0, 1 - (found - pos) * 0.1)  # further gaps score less
        pos = found + 1
    return score


class _SearchPaletteMixin:
    """Mixed into a ``Widget`` subclass that sets ``self._all``,
    ``self.query``, and ``self.height`` (max visible rows) in ``__init__``,
    then ``self._matches``/``self._index``/``self._scroll_off`` directly
    (mirroring what ``_refilter()`` would produce, since ``_all`` is already
    unfiltered at construction)."""

    def _matches_query(self, item, query: str) -> bool:
        """True if `item` matches the already-lowercased `query`. Only
        called when this widget isn't fuzzy (``self._fuzzy`` falsy) -- a
        fuzzy widget is filtered/ranked by `fuzzy_score` against
        `_search_text` instead, so a fuzzy widget need not implement this."""
        raise NotImplementedError

    def _search_text(self, item) -> str:
        """String matched/scored against the query. Default: the item
        itself (already a plain string for SearchBar/ThemePalette); override
        for items that need a different serialization (CommandPalette:
        name + description)."""
        return str(item)

    def _activate_item(self, item) -> None:
        """Called with `self._matches[self._index]` when it's picked."""
        raise NotImplementedError

    def _on_query_changed(self) -> None:
        """Hook: called after the query changes and `_matches` is
        refreshed. No-op by default; SearchBar overrides it to fire
        `on_change(query)`."""

    def _refilter(self) -> None:
        q = self.query.lower()
        if not q:
            self._matches = list(self._all)
        elif getattr(self, "_fuzzy", False):
            scored = [
                (score, it)
                for it in self._all
                if (score := fuzzy_score(self._search_text(it), q)) is not None
            ]
            scored.sort(key=lambda pair: pair[0], reverse=True)
            self._matches = [it for _, it in scored]
        else:
            self._matches = [it for it in self._all if self._matches_query(it, q)]
        self._index = 0 if self._matches else -1
        self._scroll_off = 0
        self._on_query_changed()

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
