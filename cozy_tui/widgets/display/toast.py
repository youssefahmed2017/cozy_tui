from cozy_tui._width import text_width
from cozy_tui.style import Style
from cozy_tui.widget import Widget

# level -> (border/icon color, default icon)
_LEVELS = {
    "info": ("bright_cyan", "ℹ"),
    "success": ("bright_green", "✓"),
    "warning": ("bright_yellow", "⚠"),
    "error": ("bright_red", "✗"),
}


class Toast(Widget):
    """A transient notification, usually created via :meth:`App.toast`. Drawn as a
    small bordered card that stacks with other toasts in a screen corner and
    auto-dismisses on a timer. Non-focusable and non-modal — it never steals focus
    or blocks input.
    """

    HEIGHT = 5  # border + padding + content row + padding + border
    _MAX_WIDTH = 60
    _PAD_X = 3
    _MARGIN = 1
    _GAP = 1

    def __init__(self, message, *, level="info", icon=None, corner="bottom-right"):
        super().__init__(0, 0)
        self.message = message
        self.level = level if level in _LEVELS else "info"
        color, default_icon = _LEVELS[self.level]
        self.color = color
        self.icon = default_icon if icon is None else icon
        self.corner = corner

    def _content_width(self, cols):
        inner = text_width(self.icon) + 1 + text_width(self.message)
        return min(self._MAX_WIDTH, cols - 2 * self._MARGIN, inner + 2 * self._PAD_X + 2)

    def _clip(self, text, width):
        if text_width(text) <= width:
            return text
        out = ""
        for ch in text:
            if text_width(out + ch) > width - 1:
                break
            out += ch
        return out + "…"

    def _place(self, canvas, w):
        """Top-left ``(col, row)`` for this toast given its stack."""
        cols, rows = canvas.cols, canvas.rows
        stack = getattr(canvas, "_toasts", [self])
        n = len(stack)
        j = stack.index(self) if self in stack else n - 1
        step = self.HEIGHT + self._GAP
        bottom = self.corner.startswith("bottom")
        right = self.corner.endswith("right")
        if bottom:
            k = (n - 1) - j  # newest sits nearest the bottom edge
            top = rows - 1 - self._MARGIN - k * step - (self.HEIGHT - 1)
        else:
            top = self._MARGIN + j * step
        left = (cols - self._MARGIN - w) if right else self._MARGIN
        return left, top

    def draw(self, canvas):
        bg = canvas.style.raw_bg
        w = self._content_width(canvas.cols)
        left, top = self._place(canvas, w)
        if top < 0 or top + self.HEIGHT > canvas.rows:
            return  # scrolled off the stack

        border = Style(fg=self.color, bg=bg)
        h = self.HEIGHT

        for r in range(h):  # paint the card background
            canvas.write(left, top + r, " " * w, Style(bg=bg))
        canvas.write(left, top, "╭" + "─" * (w - 2) + "╮", border)
        canvas.write(left, top + h - 1, "╰" + "─" * (w - 2) + "╯", border)
        for r in range(1, h - 1):
            canvas.write(left, top + r, "│", border)
            canvas.write(left + w - 1, top + r, "│", border)

        cy = top + h // 2
        cx = left + self._PAD_X
        canvas.write(cx, cy, self.icon, Style(fg=self.color, bg=bg))
        cx += text_width(self.icon) + 1
        canvas.write(cx, cy, self._clip(self.message, left + w - 1 - cx),
                     Style(fg="white", bg=bg, styles=["bold"]))
