from cozy_tui.style import Style, selection_style
from cozy_tui.widget import Widget
from cozy_tui.widgets.selection._search_palette import (
    _SearchPaletteMixin,
    draw_panel_frame,
)


class Command:
    """One entry in a :class:`CommandPalette`: a name, an optional one-line
    description, and the callback invoked (with no arguments) when it's
    picked. ``App.register_command(name, callback, description=...)`` builds
    these for you; construct one directly only if you're building your own
    palette outside of `App`."""

    def __init__(self, name: str, callback=None, *, description: str = ""):
        self.name = name
        self.callback = callback
        self.description = description

    def __repr__(self):
        return f"Command({self.name!r})"


class CommandPalette(_SearchPaletteMixin, Widget):
    """A searchable list of :class:`Command`\\ s, shown as a modal overlay via
    ``App.open_command_palette()`` (bound to Ctrl+P by default) -- a
    Textual-style command palette: type to filter by name or description,
    Up/Down to move, Enter or a click to run the highlighted command
    (the overlay layer handles Esc / click-outside to cancel).

    Each match renders as two lines -- a bold name and a dimmer description
    -- unlike the single-line-per-item :class:`~cozy_tui.widgets.selection.
    theme_palette.ThemePalette` this is otherwise structured just like
    (search row on top, Up/Down/Home/End/Backspace navigation, the same
    scroll-clamped overflow handling); the extra description line is the
    only real difference, since a command's name alone is rarely as
    self-explanatory as a theme's.
    """

    focusable = True

    def __init__(self, commands, *, on_select=None, width=52, height=6, style=None):
        super().__init__(
            0, 0, style or Style(fg="white", bg="black"), name="Command Palette"
        )
        self._all: list[Command] = list(commands)
        self.on_select = on_select
        self.query = ""
        self.width = max(24, width)
        self.height = max(1, height)  # max visible commands
        self._matches: list[Command] = list(self._all)
        self._index = 0 if self._matches else -1
        self._scroll_off = 0

    # ── filtering / activation ───────────────────────────────────────────────

    def _search_text(self, command: Command) -> str:
        return f"{command.name} {command.description}".lower()

    def _matches_query(self, item: Command, query: str) -> bool:
        return query in self._search_text(item)

    def _activate_item(self, item: Command) -> None:
        if self.on_select is not None:
            self.on_select(item)

    # ── Widget interface ──────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        return self.width + 2  # + left/right border

    def natural_height(self, scale) -> int:
        rows = min(self.height, max(1, len(self._matches)))
        return rows * 2 + 3  # + top border, search row, bottom border

    def contains(self, col: int, row: int) -> bool:
        return self.abs_x <= col < self.abs_x + self.natural_width(
            1
        ) and self.abs_y <= row < self.abs_y + self.natural_height(1)

    def on_mouse_click(self, col=None, row=None) -> None:
        if row is None:
            return
        rel = row - (self.abs_y + 2)  # +2: top border + search row
        if rel < 0:
            return
        idx = self._scroll_off + rel // 2  # each match spans 2 rows
        if 0 <= idx < len(self._matches):
            self._index = idx
            self._activate()

    def draw(self, canvas) -> None:
        raw_bg = self.style.raw_bg
        border = Style(fg="bright_cyan", bg=raw_bg, styles=["bold"])
        dim = Style(fg="bright_black", bg=raw_bg)
        name_style = Style(fg=self.style.fg or "white", bg=raw_bg, styles=["bold"])
        x, y, w = self.abs_x, self.abs_y, self.width
        h = self.natural_height(1)
        draw_panel_frame(canvas, x, y, w, h, border, self.style)

        search = f"🔍 {self.query}▏".ljust(w)[:w]
        canvas.write(x + 1, y + 1, search, self.style)

        if not self._matches:
            canvas.write(x + 1, y + 2, "  no matching command".ljust(w)[:w], dim)
            return

        visible = min(
            self.height, len(self._matches)
        )  # matches natural_height()'s math
        for row in range(visible):
            idx = self._scroll_off + row
            command = self._matches[idx]
            is_sel = idx == self._index
            row_y = y + 2 + row * 2
            n_style = selection_style() if is_sel else name_style
            d_style = selection_style() if is_sel else dim
            canvas.write(x + 1, row_y, ("  " + command.name).ljust(w)[:w], n_style)
            canvas.write(
                x + 1, row_y + 1, ("  " + command.description).ljust(w)[:w], d_style
            )
