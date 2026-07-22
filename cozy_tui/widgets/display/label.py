from cozy_tui._width import text_width
from cozy_tui.markup import render, slice_runs, write_runs
from cozy_tui.widget import Widget


class Label(Widget):
    """A single line of text (wrapped only when a container clips it).

    ``markup=True`` interprets inline style tags — ``"[bold red]Error[/]"`` —
    see :mod:`cozy_tui.markup`. ``text`` may be a :class:`~cozy_tui.state.State`.
    """

    def __init__(self, x, y, text, style=None, *, markup: bool = False):
        super().__init__(x, y, style)
        self.markup = markup
        # Parsed form of `text`, refreshed lazily whenever the plain attribute
        # has changed since the last look. A cache key rather than a property
        # so that `label.text = ...` (and State's setattr-based binding) stays
        # an ordinary attribute write with no widget-side plumbing.
        self._markup_key = None
        self._runs: list = []
        self._plain = ""
        self.bind("text", text)  # text may be a State
        self.laps = True

    def _sync(self) -> None:
        """Reparse if the text or base style changed. Style is part of the key
        because runs bake the base in — a theme switch mutates `self.style` in
        place, so identity alone would keep the old colors."""
        key = (self.text, self.style.fg, self.style.bg, self.style.styles)
        if self._markup_key != key:
            self._markup_key = key
            self._runs = render(self.text, self.style)
            self._plain = "".join(t for t, _s in self._runs)

    def _visible(self) -> str:
        """The text as it appears on screen — tags stripped when markup is on."""
        if not self.markup:
            return self.text
        self._sync()
        return self._plain

    def natural_width(self, scale):
        return text_width(self._visible())

    def natural_height(self, scale):
        visible = self._visible()
        if self._clip_width and visible:
            return max(1, (len(visible) + self._clip_width - 1) // self._clip_width)
        return 1

    def draw(self, canvas):
        if not self.markup:
            if self._clip_width:
                w = self._clip_width
                for i in range(0, max(1, len(self.text)), w):
                    canvas.write(
                        self.abs_x, self.abs_y + i // w, self.text[i : i + w], self.style
                    )
            else:
                canvas.write(self.abs_x, self.abs_y, self.text, self.style)
            return

        self._sync()
        if self._clip_width:
            w = self._clip_width
            for i in range(0, max(1, len(self._plain)), w):
                write_runs(
                    canvas,
                    self.abs_x,
                    self.abs_y + i // w,
                    slice_runs(self._runs, i, i + w),
                )
        else:
            write_runs(canvas, self.abs_x, self.abs_y, self._runs)
