from cozy_tui.style import Style, selection_style
from cozy_tui.widget import Widget
from cozy_tui.widgets.selection._search_palette import (
    _SearchPaletteMixin,
    draw_panel_frame,
)


class ThemePalette(_SearchPaletteMixin, Widget):
    """A searchable list of Theme modes, shown as a modal overlay via
    ``App.open_theme_palette()`` (bound to Ctrl+T by default) -- a
    scoped-down take on the "type to filter a list of commands" palette
    pattern (à la Textual's command palette), just for picking a theme.

    Type to filter by substring; Up/Down move the cursor; Enter or a click
    picks the highlighted match, calling ``on_select(mode)`` (the overlay
    layer handles Esc / click-outside to cancel). Self-contained: it draws
    its own bordered panel, so it needs no surrounding ``Box``, matching
    :class:`~cozy_tui.widgets.PromptDialog`'s approach to a single-widget
    modal.
    """

    focusable = True

    def __init__(
        self, modes, *, current=None, on_select=None, width=36, height=8, style=None
    ):
        super().__init__(0, 0, style or Style(fg="white", bg="black"))
        self._all = list(modes)
        self.on_select = on_select
        self.query = ""
        self.width = max(20, width)
        self.height = max(1, height)  # max visible rows in the match list
        self._matches: list[str] = list(self._all)
        self._index = self._all.index(current) if current in self._all else 0
        self._scroll_off = 0

    # ── filtering / activation ───────────────────────────────────────────────

    def _matches_query(self, item, query: str) -> bool:
        return query in item.lower()

    def _activate_item(self, item) -> None:
        if self.on_select is not None:
            self.on_select(item)

    # ── Widget interface ──────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        return self.width + 2  # + left/right border

    def natural_height(self, scale) -> int:
        rows = min(self.height, max(1, len(self._matches)))
        return rows + 3  # + top border, search row, bottom border

    def contains(self, col: int, row: int) -> bool:
        return self.abs_x <= col < self.abs_x + self.natural_width(
            1
        ) and self.abs_y <= row < self.abs_y + self.natural_height(1)

    def on_mouse_click(self, col=None, row=None) -> None:
        if row is None:
            return
        idx = self._scroll_off + (row - (self.abs_y + 2))  # +2: top border + search row
        if 0 <= idx < len(self._matches):
            self._index = idx
            self._activate()

    def draw(self, canvas) -> None:
        from cozy_tui.theme import get_theme  # local: theme.py builds on Style

        raw_bg = self.style.raw_bg
        border = Style(fg=get_theme().accent, bg=raw_bg, styles=["bold"])
        dim = Style(fg="bright_black", bg=raw_bg)
        x, y, w = self.abs_x, self.abs_y, self.width
        h = self.natural_height(1)
        draw_panel_frame(canvas, x, y, w, h, border, self.style)

        search = f"🔍 {self.query}▏".ljust(w)[:w]
        canvas.write(x + 1, y + 1, search, self.style)

        if not self._matches:
            canvas.write(x + 1, y + 2, "  no matching theme".ljust(w)[:w], dim)
            return

        visible = min(
            self.height, len(self._matches)
        )  # matches natural_height()'s math
        for row in range(visible):
            idx = self._scroll_off + row
            row_y = y + 2 + row
            text = ("  " + self._matches[idx].title()).ljust(w)[:w]
            style = selection_style() if idx == self._index else self.style
            canvas.write(x + 1, row_y, text, style)
