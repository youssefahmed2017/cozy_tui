from collections import deque

from cozy_tui.style import Style
from cozy_tui.widget import Widget
from cozy_tui.widgets.input._input_draw import _DrawMixin
from cozy_tui.widgets.input._input_history import _HistoryMixin
from cozy_tui.widgets.input._input_keys import _KeysMixin
from cozy_tui.widgets.input._input_mask import _MaskMixin, mask_digit_count, mask_raw


class Input(_HistoryMixin, _DrawMixin, _KeysMixin, _MaskMixin, Widget):
    focusable = True

    # Reveal icon reservation: a 1-cell gap, then a 2-cell-wide slot for the
    # glyph (a safe upper bound regardless of how a given terminal actually
    # renders it -- the click hit-zone is this fixed region, not the glyph's
    # true rendered width).
    _ICON_GAP = 1
    _ICON_WIDTH = 2

    def __init__(
        self,
        x,
        y,
        width,
        placeholder="",
        style=None,
        cursor=True,
        cursor_style="vertical",
        flash=True,
        multiline=False,
        masked=False,
        masked_symbol="*",
        inp_type="text",
        required=False,
        validator=None,
        mask=None,
    ):
        Widget.__init__(self=self, x=x, y=y, style=style, name="Input")
        if inp_type not in ("text", "number"):
            raise ValueError('inp_type must be "text" or "number"')
        if mask is not None and multiline:
            raise ValueError("mask doesn't support multiline=True")

        self.laps = True
        self.width = max(1, width)
        self.placeholder = placeholder
        self.value = ""
        self.cursor_pos = 0
        self._scroll_off = 0
        self.cursor = cursor
        self.cursor_style = cursor_style
        self.flash = flash
        self.multiline = multiline
        self.masked = masked
        self.masked_symbol = masked_symbol
        # Toggled by the eye icon / Ctrl+R (masked, single-line, unwrapped
        # fields only -- see _draw_reveal_icon); reset to False as soon as
        # this widget notices (in draw()) that it's no longer focused, so a
        # revealed password doesn't linger on screen after tabbing away.
        self._reveal_masked = False
        self.type = inp_type
        # Takes over character-acceptance entirely when set -- type="number"'s
        # own filtering is bypassed (set one or the other, not both).
        self.mask = mask
        self.required = required
        # Optional callable(value) -> True (valid) / False (invalid, generic
        # message) / an error message string. Checked after the built-in
        # required/type rules, so it only needs to cover its own business
        # logic (e.g. an email format, a range check).
        self.validator = validator
        # Nothing shows as invalid until the user actually interacts --
        # required=True on a fresh, empty field shouldn't open already red.
        self._touched = False
        self._overwrite = False
        self._sel_anchor: int | None = None
        self._masked_cache_key: str | None = None  # identity-cached masked display
        self._masked_cache_val: str = ""
        # error's identity-cached the same way: it's read from _normal_style/
        # _focused_style on every draw() -- including ones driven by an
        # unrelated animation elsewhere in the app (Tabs glide, ScrollView
        # momentum, Spinner, the cursor blink) -- so without this, a
        # validator= callable gets re-invoked ~30x/second for as long as any
        # of those run, even though self.value hasn't changed since the last
        # check. Sentinel object() (never `is` a real value) so the very
        # first call always misses the cache.
        self._error_cache_key: tuple = (object(), None)
        self._error_cache_val: str | None = None
        self._undo_stack = deque(maxlen=_HistoryMixin._MAX_HISTORY)
        self._redo_stack: list = []
        self._last_action: str | None = None
        self.laps = True

    def _reveal_icon_active(self) -> bool:
        """The eye icon only applies to a plain, single-line, unwrapped
        masked field -- the overwhelmingly common real case (a login form's
        password field). `multiline`/`_clip_width` masked inputs are a rare
        combination not worth tangling into the wrap/clip math for; they
        keep the mask-only behavior unchanged."""
        return self.masked and not self.multiline and not self._clip_width

    def natural_width(self, scale):
        if self._reveal_icon_active():
            return self.width + self._ICON_GAP + self._ICON_WIDTH
        return self.width

    # ── selection helpers ────────────────────────────────────────────────────

    def _sel_range(self) -> tuple[int, int] | None:
        """Return (start, end) selection range, or None when nothing is selected."""
        if self._sel_anchor is None or self._sel_anchor == self.cursor_pos:
            return None
        a, b = self._sel_anchor, self.cursor_pos
        return (a, b) if a < b else (b, a)

    def _sel_text(self) -> str:
        r = self._sel_range()
        return self.value[r[0] : r[1]] if r else ""

    def _clear_sel(self) -> None:
        self._sel_anchor = None

    def _delete_sel(self) -> None:
        r = self._sel_range()
        if r is None:
            return
        a, b = r
        self.value = self.value[:a] + self.value[b:]
        self.cursor_pos = a
        self._sel_anchor = None

    def _shift_move(self, new_pos: int) -> None:
        """Move cursor to new_pos while extending/creating a selection."""
        new_pos = max(0, min(new_pos, len(self.value)))
        if self._sel_anchor is None:
            self._sel_anchor = self.cursor_pos
        self.cursor_pos = new_pos
        if self.cursor_pos == self._sel_anchor:
            self._sel_anchor = None

    def _sel_style(self) -> Style:
        return Style(fg="white", bg="blue")

    # ── word-boundary helpers ────────────────────────────────────────────────

    def _word_right(self, pos: int) -> int:
        v = self.value
        n = len(v)
        while pos < n and not (v[pos].isalnum() or v[pos] == "_"):
            pos += 1
        while pos < n and (v[pos].isalnum() or v[pos] == "_"):
            pos += 1
        return pos

    def _word_left(self, pos: int) -> int:
        v = self.value
        pos -= 1
        while pos > 0 and not (v[pos].isalnum() or v[pos] == "_"):
            pos -= 1
        while pos > 0 and (v[pos - 1].isalnum() or v[pos - 1] == "_"):
            pos -= 1
        return max(0, pos)

    # ── position helpers ─────────────────────────────────────────────────────

    def _cursor_to_line_col(self):
        """Return (line_index, col) for cursor_pos within value.split('\\n')."""
        before = self.value[: self.cursor_pos]
        parts = before.split("\n")
        return len(parts) - 1, len(parts[-1])

    def _line_col_to_pos(self, line: int, col: int) -> int:
        """Convert (line, col) to a flat cursor_pos."""
        lines = self.value.split("\n")
        pos = sum(len(lines[i]) + 1 for i in range(line))
        return pos + min(col, len(lines[line]) if line < len(lines) else 0)

    def _get_cursor_screen_pos(self, scroll_y: int):
        """Return (col, row) screen coordinates for the cursor, or None."""
        w = self._clip_width or self.width

        if self.multiline:
            cur_line, cur_col = self._cursor_to_line_col()
            display_row = 0
            for li, logical_line in enumerate((self.value or "").split("\n")):
                chunks_count = (
                    max(1, (len(logical_line) + w - 1) // w) if logical_line else 1
                )
                if li == cur_line:
                    chunk_row = cur_col // w
                    return (
                        self.abs_x + (cur_col % w),
                        self.abs_y + display_row + chunk_row - scroll_y,
                    )
                display_row += chunks_count
            return None

        elif self._clip_width:
            cline = self.cursor_pos // w
            ccol = self.cursor_pos % w
            return self.abs_x + ccol, self.abs_y + cline - scroll_y

        else:
            ccol = self.cursor_pos - self._scroll_off
            if 0 <= ccol < w:
                return self.abs_x + ccol, self.abs_y - scroll_y
            return None

    def natural_height(self, scale):
        w = self._clip_width or self.width
        return self._row_count(w)

    def _row_count(self, w: int) -> int:
        if self.multiline:
            logical = self.value.split("\n") if self.value else [""]
            return sum(max(1, (len(l) + w - 1) // w) for l in logical)
        return max(1, (len(self.value) + w - 1) // w) if self.value else 1

    # ── hit-testing ──────────────────────────────────────────────────────────

    def contains(self, col: int, row: int) -> bool:
        w = self._clip_width or self.width
        if self._reveal_icon_active():
            w += self._ICON_GAP + self._ICON_WIDTH
        if self.multiline and self.value:
            h = self._row_count(w)
        elif self._clip_width and self.value:
            h = self._row_count(self._clip_width)
        else:
            h = 1
        return self.abs_x <= col < self.abs_x + w and self.abs_y <= row < self.abs_y + h

    # ── validation ───────────────────────────────────────────────────────────

    # Transient states a number field naturally passes through mid-typing
    # (a bare sign or decimal point) -- not yet a complete number, but not
    # something to flag as an error either.
    _NUMBER_IN_PROGRESS = ("", "-", ".", "-.")

    @property
    def error(self) -> str | None:
        """The current validation error message, or ``None`` if valid.
        Always ``None`` until the value has actually changed at least once --
        a fresh, untouched ``required=True`` field shouldn't open already
        red. Checked in order: ``required``, the built-in ``type``
        constraint, then ``validator`` (which only needs to cover its own
        business logic, not these).

        Cached against ``(self.value, self._touched)`` -- similar in spirit
        to ``_display_value``'s masked-cache in ``_input_draw.py`` -- since
        this is read from ``_normal_style``/``_focused_style`` on every
        ``draw()``, including ones driven by an unrelated animation
        elsewhere in the app; without the cache, a slow ``validator`` would
        get re-invoked on every such frame even though nothing here changed."""
        key = (self.value, self._touched)
        if key == self._error_cache_key:
            return self._error_cache_val
        result = self._compute_error()
        self._error_cache_key = key
        self._error_cache_val = result
        return result

    def _compute_error(self) -> str | None:
        if not self._touched:
            return None
        if self.required and not self.value:
            return "Required"
        if self.type == "number" and self.value not in self._NUMBER_IN_PROGRESS:
            try:
                float(self.value)
            except ValueError:
                return "Not a valid number"
        if self.mask is not None and self.value:
            if len(mask_raw(self.mask, self.value)) < mask_digit_count(self.mask):
                return "Incomplete"
        if self.validator is not None:
            # Unlike most callbacks in this library (which only fire on a
            # discrete user action), `error` -- and therefore `validator` --
            # runs on every draw frame via _normal_style/_focused_style, so a
            # raising validator would crash the render loop continuously
            # rather than just failing once; worth guarding specifically here.
            try:
                result = self.validator(self.value)
            except Exception as exc:
                return str(exc) or "Invalid"
            if result is False:
                return "Invalid"
            if isinstance(result, str):
                return result
        return None

    @property
    def is_valid(self) -> bool:
        return self.error is None

    def _error_color(self) -> str:
        from cozy_tui.theme import get_theme  # local: theme.py builds on Style

        return get_theme().error

    # ── styles ───────────────────────────────────────────────────────────────

    def _normal_style(self):
        if self.error is not None:
            return Style(fg=self._error_color(), bg=self.style.raw_bg)
        return self.style

    def _focused_style(self):
        if self.error is not None:
            return Style(fg="black", bg=self._error_color())
        return Style(fg="black", bg="white")

    def _placeholder_style(self, focused: bool = False):
        if focused:
            return Style(fg="bright_black", bg="white", styles=["dim"])
        raw_bg = self.style.raw_bg
        return Style(fg=self.style.fg, bg=raw_bg, styles=["dim"])

    def _cursor_style_obj(self, char_at_cursor, content_style: Style):
        fg = content_style.fg
        bg = content_style.bg
        raw_bg = bg.replace("_bg", "") if bg else None

        if self.cursor_style == "block":
            return Style(fg=raw_bg or "black", bg=fg or "white"), char_at_cursor
        else:
            return Style(fg=fg, bg=raw_bg, styles=["underline"]), char_at_cursor

    # ── mouse ────────────────────────────────────────────────────────────────

    def on_mouse_click(self, col=None, row=None):
        if (
            self._reveal_icon_active()
            and col is not None
            and row is not None
            and row == self.abs_y
            and self.abs_x + self.width + self._ICON_GAP
            <= col
            < self.abs_x + self.width + self._ICON_GAP + self._ICON_WIDTH
        ):
            self._reveal_masked = not self._reveal_masked
            return
        self._clear_sel()
        if col is not None and row is not None:
            self._set_cursor_from_mouse(col, row)
            self._sel_anchor = self.cursor_pos  # anchor for potential drag
        self._fire_click()

    def on_mouse_drag(self, col: int, row: int) -> None:
        self._set_cursor_from_mouse(col, row)

    def _set_cursor_from_mouse(self, col: int, row: int) -> None:
        """Position cursor_pos from a terminal click at (col, row)."""
        w = self._clip_width or self.width
        if self.multiline:
            target_row = row - self.abs_y
            display_row = 0
            flat_pos = 0
            value_lines = self.value.split("\n")
            for li, logical_line in enumerate(self._display_value.split("\n")):
                vline_len = len(value_lines[li]) if li < len(value_lines) else 0
                chunks_count = (
                    max(1, (len(logical_line) + w - 1) // w) if logical_line else 1
                )
                if display_row + chunks_count > target_row:
                    chunk_idx = target_row - display_row
                    col_in_chunk = max(0, col - self.abs_x)
                    pos = flat_pos + chunk_idx * w + col_in_chunk
                    self.cursor_pos = max(0, min(pos, flat_pos + vline_len))
                    return
                display_row += chunks_count
                flat_pos += vline_len + 1
            self.cursor_pos = len(self.value)
        elif self._clip_width:
            line = max(0, row - self.abs_y)
            pos = line * w + max(0, col - self.abs_x)
            self.cursor_pos = max(0, min(pos, len(self.value)))
        else:
            pos = self._scroll_off + max(0, col - self.abs_x)
            self.cursor_pos = max(0, min(pos, len(self.value)))

    def get(self):
        return self.value
