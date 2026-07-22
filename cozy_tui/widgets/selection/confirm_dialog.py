from cozy_tui._width import text_width
from cozy_tui.events import Key
from cozy_tui.style import Style, selection_style
from cozy_tui.widget import Widget
from cozy_tui.widgets.selection._search_palette import draw_panel_frame


class ConfirmDialog(Widget):
    """A Yes/No confirmation panel, designed to be shown as a modal overlay
    via ``App.confirm()``. Left/Right (or Tab/Shift+Tab) move between the two
    buttons, Enter picks the highlighted one, Y/N pick directly, a click
    picks whichever button it lands on. Esc / click-outside cancel (dismissal
    is handled by the overlay layer, which treats cancelling the same as
    "No" -- see ``App.confirm``). Self-contained: it draws its own bordered
    panel, so it needs no surrounding ``Box``, the same approach as
    :class:`~cozy_tui.widgets.PromptDialog`.
    """

    focusable = True

    def __init__(
        self,
        message: str,
        *,
        yes_label: str = "Yes",
        no_label: str = "No",
        default: bool = True,
        on_choose=None,
        width: int = 40,
        style=None,
    ):
        super().__init__(0, 0, style or Style(fg="white", bg="black"))
        self.message = message
        self.yes_label = yes_label
        self.no_label = no_label
        self.on_choose = on_choose
        self.width = max(text_width(message) + 2, 20, width)
        self._yes = bool(default)  # which button is currently highlighted

    def natural_width(self, scale) -> int:
        return self.width + 2  # + left/right border

    def natural_height(self, scale) -> int:
        return 5  # border(2) + message + buttons + hint

    def contains(self, col: int, row: int) -> bool:
        return self.abs_x <= col < self.abs_x + self.natural_width(
            1
        ) and self.abs_y <= row < self.abs_y + self.natural_height(1)

    def _choose(self, yes: bool) -> None:
        if self.on_choose is not None:
            self.on_choose(yes)

    def _button_spans(self, w: int):
        """[(text, start_col, end_col, is_yes), ...], centered within the
        panel's interior width `w` (0-based, relative to the interior)."""
        yes_text = f"[ {self.yes_label} ]"
        no_text = f"[ {self.no_label} ]"
        gap = "   "
        total = len(yes_text) + len(gap) + len(no_text)
        yes_start = max(0, (w - total) // 2)
        yes_end = yes_start + len(yes_text)
        no_start = yes_end + len(gap)
        no_end = no_start + len(no_text)
        return [
            (yes_text, yes_start, yes_end, True),
            (no_text, no_start, no_end, False),
        ]

    def on_key(self, key) -> None:
        if key in (Key.LEFT, Key.RIGHT, Key.TAB, Key.SHIFT_TAB):
            self._yes = not self._yes
        elif key == Key.ENTER:
            self._choose(self._yes)
        elif key in ("y", "Y"):
            self._choose(True)
        elif key in ("n", "N"):
            self._choose(False)

    def on_mouse_click(self, col=None, row=None) -> None:
        if col is None or row is None:
            return
        if row != self.abs_y + 2:  # border(1) + message row(1)
            return
        rel_col = col - (self.abs_x + 1)
        for _text, start, end, is_yes in self._button_spans(self.width):
            if start <= rel_col < end:
                self._yes = is_yes
                self._choose(is_yes)
                return

    def draw(self, canvas) -> None:
        from cozy_tui.theme import get_theme  # local: theme.py builds on Style

        raw_bg = self.style.raw_bg
        border = Style(fg=get_theme().accent, bg=raw_bg, styles=["bold"])
        dim = Style(fg="bright_black", bg=raw_bg)
        x, y, w = self.abs_x, self.abs_y, self.width
        h = self.natural_height(1)
        draw_panel_frame(canvas, x, y, w, h, border, self.style)

        canvas.write(x + 1, y + 1, (" " + self.message).ljust(w)[:w], self.style)

        for text, start, end, is_yes in self._button_spans(w):
            style = selection_style() if is_yes == self._yes else self.style
            canvas.write(x + 1 + start, y + 2, text, style)

        canvas.write(x + 1, y + 3, "  Y/N or Enter    Esc: cancel".ljust(w)[:w], dim)
