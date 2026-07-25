"""Tiny inline charts drawn from Unicode block glyphs -- no dependency, no
canvas, just cells. `Sparkline` is a one-row trend line; `BarChart` is a stack
of horizontal bars. Both take plain numbers and both accept a
:class:`~cozy_tui.state.State`, so a live feed is `chart.data = state` once."""

from cozy_tui.widget import Widget


def _fmt(v) -> str:
    """A compact label for a value: an int stays an int, a float keeps one
    decimal (so `3.0` reads as `3`, `3.14` as `3.1`)."""
    f = float(v)
    return str(int(f)) if f.is_integer() else f"{f:.1f}"


def _accent(style):
    """The bar color to use when none is given -- the active theme's accent,
    resolved at draw time so a theme switch follows. Imported locally because
    theme.py builds on Style."""
    from cozy_tui.theme import get_theme

    from cozy_tui.style import Style

    return Style(fg=get_theme().accent, bg=style.raw_bg)


class Sparkline(Widget):
    """A one-row trend line: each value becomes one of eight block heights
    (``▁▂▃▄▅▆▇█``), scaled between the data's min and max (or an explicit
    ``minimum``/``maximum``). ``width`` caps how many cells show -- the most
    recent that many values, so a `push()`-fed line scrolls left. ``values``
    may be a :class:`~cozy_tui.state.State`.
    """

    focusable = False
    _BARS = "▁▂▃▄▅▆▇█"  # eight levels, low → high

    def __init__(
        self,
        x,
        y,
        values=None,
        *,
        width: int | None = None,
        minimum=None,
        maximum=None,
        style=None,
    ):
        super().__init__(x, y, style)
        self.width = width
        self.minimum = minimum
        self.maximum = maximum
        # Not wrapped in list(): bind() resolves a State itself, and _shown()
        # copies before reading, so a plain list needs no defensive copy here.
        self.bind("values", values if values is not None else [])

    def push(self, value) -> "Sparkline":
        """Append a value (trimming to ``width`` if set) -- the live-feed form,
        for driving the line from a timer without a State."""
        vals = list(self.values)
        vals.append(value)
        if self.width is not None:
            vals = vals[-self.width :]
        self.values = vals
        return self

    def _shown(self) -> list:
        vals = list(self.values)
        if self.width is not None and len(vals) > self.width:
            return vals[-self.width :]
        return vals

    def natural_width(self, scale) -> int:
        return self.width if self.width is not None else len(self.values)

    def natural_height(self, scale) -> int:
        return 1

    def _line(self) -> str:
        vals = self._shown()
        if not vals:
            return ""
        lo = self.minimum if self.minimum is not None else min(vals)
        hi = self.maximum if self.maximum is not None else max(vals)
        span = hi - lo
        out = []
        for v in vals:
            frac = (v - lo) / span if span > 0 else 0.5
            idx = max(0, min(7, round(frac * 7)))
            out.append(self._BARS[idx])
        return "".join(out)

    def draw(self, canvas) -> None:
        canvas.write(self.abs_x, self.abs_y, self._line(), self.style)


class BarChart(Widget):
    """A column of horizontal bars, one row per item, drawn to eighth-of-a-cell
    precision (``█…▏``). ``data`` is a list of ``(label, value)`` pairs (a
    ``(label, value, color)`` triple colors that one bar), a ``{label: value}``
    dict, or a bare list of numbers; it may be a
    :class:`~cozy_tui.state.State`. Bars scale to ``maximum`` (default: the
    largest value). ``show_values`` prints each value after its bar.
    """

    focusable = False
    _EIGHTHS = " ▏▎▍▌▋▊▉█"  # index 0..8 = that many eighths filled

    def __init__(
        self,
        x,
        y,
        data=None,
        *,
        width: int = 30,
        maximum=None,
        show_values: bool = True,
        bar_style=None,
        style=None,
    ):
        super().__init__(x, y, style)
        self.width = width
        self.maximum = maximum
        self.show_values = show_values
        self.bar_style = bar_style  # Style for every bar; None → theme accent
        self.bind("data", data if data is not None else [])

    def _items(self) -> list[tuple[str, float, object]]:
        """Normalize `data` to ``(label, value, color)`` rows -- color is None
        unless the item was a 3-tuple carrying one."""
        data = self.data
        if isinstance(data, dict):
            data = list(data.items())
        rows = []
        for item in data:
            if isinstance(item, (tuple, list)):
                label, value = item[0], item[1]
                color = item[2] if len(item) > 2 else None
            else:
                label, value, color = "", item, None
            rows.append((str(label), float(value), color))
        return rows

    def natural_width(self, scale) -> int:
        return self.width

    def natural_height(self, scale) -> int:
        return len(self._items())

    def _bar(self, value: float, top: float, cells: int) -> str:
        """A `cells`-wide bar for `value` against `top`, padded with spaces."""
        if top <= 0 or cells <= 0:
            return " " * max(0, cells)
        eighths = max(0, min(cells * 8, round(value / top * cells * 8)))
        full, rem = divmod(eighths, 8)
        bar = "█" * full + (self._EIGHTHS[rem] if rem else "")
        return bar.ljust(cells)

    def draw(self, canvas) -> None:
        rows = self._items()
        if not rows:
            return
        labels = [label for label, _v, _c in rows]
        values = [value for _l, value, _c in rows]
        top = self.maximum if self.maximum is not None else max(values, default=0)

        label_w = max((len(label) for label in labels), default=0)
        vstrs = [_fmt(v) for v in values] if self.show_values else [""] * len(rows)
        value_w = max((len(s) for s in vstrs), default=0)

        # width = [label] " " [bar] (" " [value])? -- carve the fixed parts off,
        # the bar gets what's left (at least one cell).
        used = label_w + (1 if label_w else 0)
        if self.show_values:
            used += value_w + 1
        bar_cells = max(1, self.width - used)

        default_bar = None  # resolved lazily, shared across bars without a color
        for i, (label, value, color) in enumerate(rows):
            x = self.abs_x
            y = self.abs_y + i
            if label_w:
                canvas.write(x, y, label.rjust(label_w), self.style)
                x += label_w + 1
            if color is not None:
                from cozy_tui.style import Style

                bar_style = Style(fg=color, bg=self.style.raw_bg)
            elif self.bar_style is not None:
                bar_style = self.bar_style
            else:
                default_bar = default_bar or _accent(self.style)
                bar_style = default_bar
            canvas.write(x, y, self._bar(value, top, bar_cells), bar_style)
            x += bar_cells
            if self.show_values:
                canvas.write(x + 1, y, vstrs[i].rjust(value_w), self.style)
