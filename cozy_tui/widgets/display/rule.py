from cozy_tui._width import char_width, text_width
from cozy_tui.widget import Widget


class Rule(Widget):
    """A horizontal or vertical divider line, optionally titled.

    Replaces the ``Label(x, y, "─" * n)`` idiom for separating sections. A Rule
    sizes itself to fill its container rather than hardcoding a width, so it
    follows a resize:

    - inside a ``Box``, a bare ``box.add(Rule(1, 4))`` spans from its ``x`` to
      the box's far interior edge — the divider-in-a-panel case;
    - docked (``app.dock``/``box.dock``) or stretched (a ``VBox``/``HBox`` child
      with ``align="stretch"``), it fills the assigned band;
    - ``length=`` forces an explicit size in cells instead of auto-filling.

    ``title`` labels a **horizontal** rule — ``── Setup ─────────`` — and may be
    a :class:`~cozy_tui.state.State`. ``char`` overrides the line glyph (default
    ``─`` horizontal, ``│`` vertical). Rules are decorative: never focusable.
    """

    focusable = False

    _CHARS = {"horizontal": "─", "vertical": "│"}
    _DEFAULT = 12  # fallback when there's nothing to measure against

    def __init__(
        self,
        x=0,
        y=0,
        *,
        length: int | None = None,
        orientation: str = "horizontal",
        title="",
        char: str | None = None,
        style=None,
    ):
        super().__init__(x, y, style)
        if orientation not in self._CHARS:
            raise ValueError(
                f"orientation must be 'horizontal' or 'vertical', got {orientation!r}"
            )
        self.orientation = orientation
        self.length = length
        self.char = char if char is not None else self._CHARS[orientation]
        self.bind("title", title)  # shown only when horizontal; may be a State
        self._target_len: int | None = None  # set when docked / stretched
        # Treated as lapping so an auto-filling Rule is clipped to its Box rather
        # than growing it (which, since its own width is derived from the box's,
        # would feed back frame over frame).
        self.laps = True

    def dock_resize(self, w, h, scale) -> None:
        self._target_len = w if self.orientation == "horizontal" else h

    def _length(self, scale) -> int:
        if self.length is not None:
            return max(0, self.length)
        if self._target_len is not None:
            return max(0, self._target_len)
        parent = self.parent
        # A bare `box.add(Rule(x, y))` fills from its offset to the box's far
        # interior edge -- the mid-content divider case, which docking can't
        # cover because the rule sits between children, not on an edge. Detected
        # by duck-typing a Box (its own `border` + pixel `width`/`height`).
        if parent is not None and hasattr(parent, "border") and hasattr(parent, "width"):
            if self.orientation == "horizontal":
                return max(1, parent.width // scale - self.x + 1)
            return max(1, parent.height // scale - self.y + 1)
        return self._DEFAULT

    def natural_width(self, scale) -> int:
        return self._length(scale) if self.orientation == "horizontal" else 1

    def natural_height(self, scale) -> int:
        return 1 if self.orientation == "horizontal" else self._length(scale)

    def _line(self, n: int) -> str:
        """The horizontal rule as a string of exactly ``n`` display cells."""
        title = self.title
        if not title:
            return self.char * n
        head = self.char * 2 + f" {title} "  # ── Title
        head_w = text_width(head)
        if head_w >= n:  # title alone overruns the rule -- clip it to fit
            return _clip_cells(head, n)
        return head + self.char * (n - head_w)

    def draw(self, canvas) -> None:
        n = self._length(canvas.SCALE)
        if n <= 0:
            return
        if self.orientation == "vertical":
            for i in range(n):
                canvas.write(self.abs_x, self.abs_y + i, self.char, self.style)
            return
        canvas.write(self.abs_x, self.abs_y, self._line(n), self.style)


def _clip_cells(s: str, n: int) -> str:
    """`s` truncated to at most `n` display cells (wide glyphs counted whole)."""
    out, width = [], 0
    for ch in s:
        cw = char_width(ch)
        if width + cw > n:
            break
        out.append(ch)
        width += cw
    return "".join(out)
