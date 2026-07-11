from cozy_tui._width import clip_text, text_width
from cozy_tui.style import Style
from cozy_tui.widget import Widget

# level -> default icon. The border/icon *color* instead comes from the
# active theme's same-named role (theme.info/success/warning/error), so
# switching themes re-colors toasts too.
_ICONS = {
    "info": "ℹ",
    "success": "✓",
    "warning": "⚠",
    "error": "✗",
}


class Toast(Widget):
    """A transient notification, usually created via :meth:`App.toast`. Drawn as a
    small bordered card that stacks with other toasts in a screen corner and
    auto-dismisses on a timer. Non-focusable and non-modal — it never steals
    keyboard focus (Tab can't reach it either way, since only a *modal*
    overlay's subtree is ever Tab-reachable) or blocks input elsewhere.

    ``actions`` (usually passed via ``App.toast(..., actions=[...])``) turns
    it into a small interactive card: a row of ``[ Label ]`` buttons under
    the message, each firing ``on_action(index)`` when clicked (App wires
    this to the matching callback and dismissal). Clicking a button never
    moves ``app.focused`` -- see ``App._hit_non_modal_overlay`` -- so a plain
    click on an actionable toast still can't steal focus either.
    """

    HEIGHT = 5  # border + padding + content row(s) + padding + border
    _MAX_WIDTH = 60
    _PAD_X = 3
    _MARGIN = 1
    _GAP = 1

    def __init__(
        self, message, *, level="info", icon=None, corner="bottom-right", actions=None
    ):
        super().__init__(0, 0, name="Toast")
        from cozy_tui.theme import get_theme  # local: theme.py builds on Style

        self.message = message
        self.level = level if level in _ICONS else "info"
        self.color = getattr(get_theme(), self.level)
        self.icon = _ICONS[self.level] if icon is None else icon
        self.corner = corner
        self.actions: list = list(actions) if actions else []  # [(label, cb|None), ...]
        self._action_handler = None
        # (left, top, w, h) from the last draw() -- Toast positions itself
        # freshly every frame via _place() rather than self.x/self.y, so
        # contains()/on_mouse_click() need this cache instead of the usual
        # abs_x/abs_y (see Box._bounds for the same pattern). (0,0,0,0)
        # until the first draw() means "not hit-testable yet".
        self._bounds = (0, 0, 0, 0)

    # ── actions ──────────────────────────────────────────────────────────────

    def on_action(self, func):
        """Register a callback invoked with the index (into ``self.actions``)
        of the action button that was clicked."""
        self._action_handler = func
        return self

    def _fire_action(self, index: int) -> None:
        if self._action_handler is not None:
            self._action_handler(index)

    def _button_row_spans(self, left: int, w: int):
        """[(label, index, start_col, end_col), ...] in absolute canvas
        columns, centered within the card's interior (``w`` minus its 2
        border columns) -- same shape as ConfirmDialog's own button-span
        math, just in absolute coordinates since Toast already draws that
        way (see ``_place()``)."""
        texts = [f"[ {label} ]" for label, _ in self.actions]
        gap = "  "
        total = sum(len(t) for t in texts) + len(gap) * (len(texts) - 1)
        start = left + 1 + max(0, (w - 2 - total) // 2)
        spans = []
        for i, text in enumerate(texts):
            end = start + len(text)
            spans.append((text, i, start, end))
            start = end + len(gap)
        return spans

    # ── sizing / stacking ────────────────────────────────────────────────────

    def _content_width(self, cols):
        inner = text_width(self.icon) + 1 + text_width(self.message)
        if self.actions:
            texts = [f"[ {label} ]" for label, _ in self.actions]
            btn_width = sum(len(t) for t in texts) + 2 * (len(texts) - 1)
            inner = max(inner, btn_width)
        return min(
            self._MAX_WIDTH, cols - 2 * self._MARGIN, inner + 2 * self._PAD_X + 2
        )

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

    # ── hit-testing / mouse ──────────────────────────────────────────────────

    def contains(self, col: int, row: int) -> bool:
        left, top, w, h = self._bounds
        return left <= col < left + w and top <= row < top + h

    def on_mouse_click(self, col=None, row=None) -> None:
        if not self.actions or col is None or row is None:
            return
        left, top, w, _h = self._bounds
        if row != top + 2:  # the button row -- see draw()
            return
        for _text, index, start, end in self._button_row_spans(left, w):
            if start <= col < end:
                self._fire_action(index)
                return

    def draw(self, canvas):
        bg = canvas.style.raw_bg
        w = self._content_width(canvas.cols)
        left, top = self._place(canvas, w)
        h = self.HEIGHT
        if top < 0 or top + h > canvas.rows:
            self._bounds = (0, 0, 0, 0)  # scrolled off the stack: not hit-testable
            return
        self._bounds = (left, top, w, h)

        border = Style(fg=self.color, bg=bg)

        for r in range(h):  # paint the card background
            canvas.write(left, top + r, " " * w, Style(bg=bg))
        canvas.write(left, top, "╭" + "─" * (w - 2) + "╮", border)
        canvas.write(left, top + h - 1, "╰" + "─" * (w - 2) + "╯", border)
        for r in range(1, h - 1):
            canvas.write(left, top + r, "│", border)
            canvas.write(left + w - 1, top + r, "│", border)

        # With actions, the message sits right below the border and a button
        # row takes the line that would otherwise be centering padding;
        # without them, the message alone is vertically centered as before.
        msg_row = top + 1 if self.actions else top + h // 2
        cx = left + self._PAD_X
        canvas.write(cx, msg_row, self.icon, Style(fg=self.color, bg=bg))
        cx += text_width(self.icon) + 1
        canvas.write(
            cx,
            msg_row,
            clip_text(self.message, left + w - 1 - cx),
            Style(fg="white", bg=bg, styles=["bold"]),
        )

        if self.actions:
            btn_style = Style(fg=self.color, bg=bg, styles=["bold"])
            for text, _index, start, _end in self._button_row_spans(left, w):
                canvas.write(start, top + 2, text, btn_style)
