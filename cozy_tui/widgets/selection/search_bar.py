from cozy_tui.events import Key
from cozy_tui.style import Style, selection_style
from cozy_tui.widget import Widget
from cozy_tui.widgets.selection._search_palette import _SearchPaletteMixin


class SearchBar(_SearchPaletteMixin, Widget):
    """An inline, non-modal search box: a one-line query field with a live,
    scroll-clamped list of matches shown directly beneath it -- the same
    query-filtered-list pattern ThemePalette/CommandPalette/FilePicker share
    (see ``_search_palette.py``), just embedded in your own layout (``.add()``
    it like any other widget) instead of shown as a modal overlay. Unlike
    those three, it's borderless (matching :class:`ListView`'s bare-rows
    look) -- wrap it in a :class:`~cozy_tui.widgets.Box` yourself if you want
    a border.

    Type to filter ``items``; Up/Down/Home/End move the highlighted match;
    Enter or a click fires ``on_select(value)``; Esc clears the query --
    there's no modal to cancel out of, so clearing is the closest inline
    equivalent. ``fuzzy_searching=True`` switches from substring matching to
    ranked subsequence matching (see ``fuzzy_score`` in ``_search_palette.py``):
    query characters need only appear in order, not contiguously, and
    matches are reordered by score instead of kept in ``items`` order.
    """

    focusable = True

    def __init__(
        self,
        x,
        y,
        items: list[str] | None = None,
        *,
        width: int = 30,
        height: int = 6,
        placeholder: str = "",
        fuzzy_searching: bool = False,
        style=None,
    ):
        super().__init__(x, y, style, name="Search Bar")
        self._all: list[str] = list(items) if items is not None else []
        self.query = ""
        self.placeholder = placeholder
        self._fuzzy = fuzzy_searching
        self.width = max(4, width)
        self.height = max(1, height)  # max visible match rows (query row is separate)
        self._matches: list[str] = list(self._all)
        self._index = 0 if self._matches else -1
        self._scroll_off = 0
        self._select_handler = None
        self._query_handler = None

    # ── item list API (mirrors ListView) ────────────────────────────────────

    def set_items(self, items: list[str]) -> None:
        """Replace the full candidate list and re-apply the current query."""
        self._all = list(items)
        self._refilter()

    def append(self, item: str) -> None:
        self._all.append(item)
        self._refilter()

    def clear(self) -> None:
        """Empty the candidate list and the query."""
        self._all = []
        self.query = ""
        self._refilter()

    # ── read state ───────────────────────────────────────────────────────────

    @property
    def matches(self) -> list[str]:
        """The currently filtered (and, if `fuzzy_searching`, ranked) matches."""
        return list(self._matches)

    @property
    def selected(self) -> str | None:
        """The highlighted match, or `None` if there isn't one."""
        return (
            self._matches[self._index]
            if 0 <= self._index < len(self._matches)
            else None
        )

    def get(self) -> str | None:
        return self.selected

    # ── callbacks ────────────────────────────────────────────────────────────

    def on_select(self, func):
        """Register a callback invoked with the matched string when Enter is
        pressed or a match is clicked."""
        self._select_handler = func
        return self

    def on_change(self, func):
        """Register a callback invoked with the current query text every
        time it changes (a keystroke, Esc clearing it, or `clear()`)."""
        self._query_handler = func
        return self

    # ── _SearchPaletteMixin hooks ────────────────────────────────────────────

    def _matches_query(self, item: str, query: str) -> bool:
        return query in item.lower()

    def _activate_item(self, item: str) -> None:
        if self._select_handler is not None:
            self._select_handler(item)

    def _on_query_changed(self) -> None:
        if self._query_handler is not None:
            self._query_handler(self.query)

    # ── keys ─────────────────────────────────────────────────────────────────

    def on_key(self, key) -> None:
        if key == Key.ESC:
            # SearchBar isn't modal/an overlay, so there's no "cancel" for Esc
            # to do instead -- clearing the query is the closest equivalent.
            if self.query:
                self.query = ""
                self._refilter()
            return
        super().on_key(key)  # _SearchPaletteMixin: Up/Down/Home/End/Enter/typing

    # ── Widget interface ─────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        return self.width

    def natural_height(self, scale) -> int:
        rows = min(self.height, max(1, len(self._matches)))
        return 1 + rows  # + the query row

    def on_mouse_click(self, col=None, row=None) -> None:
        if row is None:
            return
        rel = row - (self.abs_y + 1)  # +1: the query row above the match list
        if rel < 0:
            return  # clicked the query row itself
        idx = self._scroll_off + rel
        if 0 <= idx < len(self._matches):
            self._index = idx
            self._activate()

    def draw(self, canvas) -> None:
        focused = canvas.focused is self
        w = self.width
        raw_bg = self.style.raw_bg

        if self.query:
            text = self.query + ("▏" if focused else "")
            q_style = self.style
        elif focused:
            text = "▏"
            q_style = self.style
        else:
            text = self.placeholder
            q_style = Style(fg="bright_black", bg=raw_bg, styles=["dim"])
        canvas.write(self.abs_x, self.abs_y, f"🔍 {text}".ljust(w)[:w], q_style)

        dim = Style(fg="bright_black", bg=raw_bg)
        if not self._matches:
            canvas.write(self.abs_x, self.abs_y + 1, "  no matches".ljust(w)[:w], dim)
            return

        visible = min(
            self.height, len(self._matches)
        )  # matches natural_height()'s math
        for row in range(visible):
            idx = self._scroll_off + row
            is_sel = idx == self._index
            text = ("  " + self._matches[idx]).ljust(w)[:w]
            if focused and is_sel:
                style = selection_style()
            elif is_sel:
                style = selection_style(dim=True)
            else:
                style = self.style
            canvas.write(self.abs_x, self.abs_y + 1 + row, text, style)
