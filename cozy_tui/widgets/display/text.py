import textwrap

from cozy_tui.events import Key
from cozy_tui.markup import render, slice_runs, split_lines, write_runs
from cozy_tui.style import Style
from cozy_tui.widget import Widget


class Text(Widget):
    """A read-only text widget with word wrapping, alignment, and scrolling.

    Example::

        article = "Lorem ipsum dolor sit amet, consectetur adipiscing elit..."
        t = Text(2, 2, article, size="50x10", show_border=True)
        app.add(t)
        app.focus(t)  # enables ↑ ↓ PageUp PageDown scrolling

    ``size`` is a ``"WIDTHxHEIGHT"`` string in **character cells** (unlike
    :class:`Box`/:class:`ScrollView`, it is *not* virtual pixels — width is the
    wrap column, height the visible line count). Omit it to auto-size from the
    content instead. When show_border=True the border dims when unfocused and
    turns bold white when focused; width/height refer to the inner text area,
    so the widget's total footprint is width+2 × height+2.
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
        markup: bool = False,
        style=None,
    ):
        super().__init__(x, y, style)
        self.width, self.height = map(int, size.split("x")) if size else (None, None)
        self.align = align
        self.show_border = show_border
        self.markup = markup
        self._scroll_off: int = 0
        self._lines_cache: list[str] | None = None
        self._run_lines_cache: list[list] | None = None
        self._build_key = None
        # Last, not first: assigning through the `text` property resets the
        # wrap cache and scroll offset, so both must already exist. A State
        # here re-enters that same setter on every change, which is exactly
        # what re-wraps the new content.
        self.bind("text", text)

    # ── content API ──────────────────────────────────────────────────────────

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        self._text = value
        self._lines_cache = None
        self._run_lines_cache = None
        self._scroll_off = 0

    def set(self, text: str) -> None:
        self.text = text

    # ── line wrapping ─────────────────────────────────────────────────────────

    def _wrap(self, para: str) -> list[str]:
        w = self.width or 0
        if not para.strip():
            return [""]
        if not w:
            return [para]
        wrapped = textwrap.wrap(
            para, width=w, replace_whitespace=False, drop_whitespace=False
        )
        return wrapped if wrapped else [""]

    def _build(self) -> None:
        """Wrap the content into `_lines_cache`, and — when markup is on — the
        matching per-line run lists.

        Both are built in one pass so they can never drift out of step: the
        styled version slices its runs by the *plain* line lengths this
        produces, which is only sound because `_wrap` (with `drop_whitespace`
        and `replace_whitespace` off) loses no characters, so a paragraph's
        wrapped segments concatenate back to the paragraph exactly. The one
        deliberate exception is a blank paragraph, collapsed to "" here and to
        an empty run list there.
        """
        source = self._text
        paras = source.splitlines()
        if self.markup:
            runs = render(source, self.style)
            para_runs = split_lines(runs)
            paras = ["".join(t for t, _s in line) for line in para_runs]
        else:
            para_runs = None

        lines: list[str] = []
        run_lines: list[list] = []
        for i, para in enumerate(paras):
            segments = self._wrap(para)
            lines.extend(segments)
            if para_runs is None:
                continue
            offset = 0
            for segment in segments:
                run_lines.append(slice_runs(para_runs[i], offset, offset + len(segment)))
                offset += len(segment)

        if not lines:
            lines = [""]
            run_lines = [[]]
        self._lines_cache = lines
        self._run_lines_cache = run_lines if para_runs is not None else None
        self._build_key = self._key()

    def _key(self):
        # Everything _build reads besides the text (which invalidates the cache
        # through its own setter). The style triple is in here because markup
        # runs bake the base style in, and a theme switch re-colors `self.style`
        # in place rather than replacing it.
        return (
            self.width,
            self.markup,
            self.style.fg,
            self.style.bg,
            self.style.styles,
        )

    def _get_lines(self) -> list[str]:
        if self._lines_cache is None or self._build_key != self._key():
            self._build()
        return self._lines_cache

    def _get_run_lines(self) -> list[list]:
        self._get_lines()
        return self._run_lines_cache or []

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

        run_lines = self._get_run_lines() if self.markup else None

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

            if run_lines is None:
                canvas.write(tx, ty + row_off, display, self.style)
                continue
            # Paint the padded row in the base style first (so alignment
            # padding and the cleared tail keep the widget's own background),
            # then overwrite just the text with its styled runs. `display`
            # already encodes the alignment, so the indent is simply how much
            # of it comes before the text.
            canvas.write(tx, ty + row_off, display, self.style)
            # Where the text starts within `display` — derived from the
            # alignment rather than by measuring `display`'s leading spaces,
            # which would also swallow any the wrapped line legitimately owns.
            pad = max(0, w - len(line[:w]))
            indent = pad if self.align == "right" else pad // 2 if self.align == "center" else 0
            runs = run_lines[idx] if idx < len(run_lines) else []
            write_runs(canvas, tx + indent, ty + row_off, slice_runs(runs, 0, w))
