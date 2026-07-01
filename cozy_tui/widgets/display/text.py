import textwrap

from cozy_tui.events import Key
from cozy_tui.style import Style
from cozy_tui.widget import Widget


class Text(Widget):
    """A read-only text widget with word wrapping, alignment, and scrolling.

    Example::

        article = "Lorem ipsum dolor sit amet, consectetur adipiscing elit..."
        t = Text(2, 2, article, width=50, height=10, show_border=True)
        app.add(t)
        app.focus(t)  # enables ↑ ↓ PageUp PageDown scrolling

    When show_border=True the border dims when unfocused and turns bold white
    when focused.  width/height refer to the inner text area; the widget's
    total footprint is width+2 × height+2.
    """

    focusable = True

    def __init__(
        self,
        x,
        y,
        text: str = "",
        *,
        size: str | None = None,
        align: str = "left",
        show_border: bool = False,
        style=None,
    ):
        super().__init__(x, y, style)
        self._text = text
        self.width, self.height = map(int, size.split("x")) if size else None
        self.align = align
        self.show_border = show_border
        self._scroll_off: int = 0
        self._lines_cache: list[str] | None = None

    # ── content API ──────────────────────────────────────────────────────────

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        self._text = value
        self._lines_cache = None
        self._scroll_off = 0

    def set(self, text: str) -> None:
        self.text = text

    # ── line wrapping ─────────────────────────────────────────────────────────

    def _get_lines(self) -> list[str]:
        if self._lines_cache is not None:
            return self._lines_cache
        w = self.width or 0
        lines: list[str] = []
        for para in self._text.splitlines():
            if not para.strip():
                lines.append("")
            elif w:
                wrapped = textwrap.wrap(
                    para,
                    width=w,
                    replace_whitespace=False,
                    drop_whitespace=False,
                )
                lines.extend(wrapped if wrapped else [""])
            else:
                lines.append(para)
        if not lines:
            lines = [""]
        self._lines_cache = lines
        return lines

    # ── Widget interface ──────────────────────────────────────────────────────

    def _inner_width(self) -> int:
        if self.width:
            return self.width
        return max((len(line) for line in self._get_lines()), default=0)

    def _inner_height(self) -> int:
        if self.height:
            return self.height
        return max(1, len(self._get_lines()))

    def natural_width(self, scale) -> int:
        w = self._inner_width()
        return w + 2 if self.show_border else w

    def natural_height(self, scale) -> int:
        h = self._inner_height()
        return h + 2 if self.show_border else h

    def contains(self, col: int, row: int) -> bool:
        w = self.natural_width(1)
        h = self.natural_height(1)
        return self.abs_x <= col < self.abs_x + w and self.abs_y <= row < self.abs_y + h

    def on_key(self, key) -> None:
        lines = self._get_lines()
        vis = self._inner_height()
        max_scroll = max(0, len(lines) - vis)

        if key in (Key.UP, Key.SCROLL_UP):
            self._scroll_off = max(0, self._scroll_off - 1)
        elif key in (Key.DOWN, Key.SCROLL_DOWN):
            self._scroll_off = min(max_scroll, self._scroll_off + 1)
        elif key == Key.PAGE_UP:
            self._scroll_off = max(0, self._scroll_off - vis)
        elif key == Key.PAGE_DOWN:
            self._scroll_off = min(max_scroll, self._scroll_off + vis)
        elif key == Key.HOME:
            self._scroll_off = 0
        elif key == Key.END:
            self._scroll_off = max_scroll

    def draw(self, canvas) -> None:
        is_focused = canvas.focused is self
        lines = self._get_lines()
        w = self._inner_width()
        vis = self._inner_height()
        tx = self.abs_x  # text origin x
        ty = self.abs_y  # text origin y

        if self.show_border:
            border_style = (
                Style(fg="bright_white", styles=["bold"])
                if is_focused
                else Style(fg="bright_black")
            )
            bx = self.abs_x
            by = self.abs_y
            # Top
            canvas.write(bx, by, "┌" + "─" * w + "┐", border_style)
            # Sides (drawn alongside content rows below)
            # Bottom
            canvas.write(bx, by + vis + 1, "└" + "─" * w + "┘", border_style)
            tx = bx + 1
            ty = by + 1

        for row_off in range(vis):
            idx = self._scroll_off + row_off
            line = lines[idx] if idx < len(lines) else ""

            if self.align == "right":
                display = line[:w].rjust(w)
            elif self.align == "center":
                display = line[:w].center(w)
            else:
                display = line[:w].ljust(w)

            if self.show_border:
                canvas.write(tx - 1, ty + row_off, "│", border_style)
                canvas.write(tx + w, ty + row_off, "│", border_style)

            canvas.write(tx, ty + row_off, display, self.style)
