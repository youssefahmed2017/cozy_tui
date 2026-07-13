"""Digit-mask formatting for `Input(mask=...)` -- e.g. `"####-####-####-####"`
for a credit-card number. `#` is a digit slot; any other character is a
literal separator auto-inserted at that position.

`self.value` is always kept exactly equal to `mask_format(mask, raw_digits)`
for some prefix of typed digits -- e.g. `""`, `"4"`, `"411"`, `"4111-"`,
`"4111-11"`, ... -- so every *other* part of Input (rendering, validators,
copy/cut, navigation) keeps reading `self.value`/`cursor_pos` completely
unchanged, exactly like it does today. Only the four editing operations
below (insert/backspace/delete/paste) need to know about the mask at all.
"""


def mask_digit_count(mask: str) -> int:
    return mask.count("#")


def mask_format(mask: str, raw: str) -> str:
    """Rebuild the mask-conformant display string from raw digits. A
    literal character is appended as soon as it's reached -- even "ahead
    of" the next digit -- which is why typing a group's last digit shows
    the trailing separator immediately, not only once the next digit
    starts. Stops the moment raw digits run out at a `#` slot."""
    out = []
    ri = 0
    for ch in mask:
        if ch == "#":
            if ri >= len(raw):
                break
            out.append(raw[ri])
            ri += 1
        else:
            out.append(ch)
    return "".join(out)


def mask_raw(mask: str, value: str) -> str:
    """Recover the raw digits out of a mask-conformant `value` -- safe
    because `value` is always exactly `mask_format(mask, some_raw_prefix)`,
    so position `i` is a raw digit whenever `mask[i] == "#"`."""
    return "".join(ch for i, ch in enumerate(value) if i < len(mask) and mask[i] == "#")


def mask_raw_index_at(mask: str, pos: int) -> int:
    """How many digit-slots precede formatted position `pos` -- i.e. the
    raw-digit index the cursor logically sits at."""
    ri = 0
    for i, ch in enumerate(mask):
        if i >= pos:
            break
        if ch == "#":
            ri += 1
    return ri


def mask_pos_for_raw_index(mask: str, raw_index: int, formatted: str) -> int:
    """Inverse of `mask_raw_index_at`: the formatted-string position right
    after `raw_index` digits have been consumed, including any literal(s)
    immediately following the last consumed digit (so the cursor hops past
    a newly-appeared separator too)."""
    ri = 0
    pos = 0
    for ch in mask:
        if pos >= len(formatted):
            break
        if ch == "#":
            if ri == raw_index:
                break
            ri += 1
            pos += 1
        else:
            pos += 1
    return pos


class _MaskMixin:
    def _mask_replace_raw_range(self, start: int, end: int, insert: str) -> None:
        """Shared core: replace raw digits [start:end) with `insert` (also
        raw digits), reformat, and reposition the cursor right after the
        inserted digits."""
        raw = mask_raw(self.mask, self.value)
        new_raw = raw[:start] + insert + raw[end:]
        self.value = mask_format(self.mask, new_raw)
        self.cursor_pos = mask_pos_for_raw_index(
            self.mask, start + len(insert), self.value
        )

    def _mask_selection_raw_range(self) -> tuple[int, int] | None:
        r = self._sel_range()
        if r is None:
            return None
        a, b = r
        return mask_raw_index_at(self.mask, a), mask_raw_index_at(self.mask, b)

    def _mask_insert_digit(self, ch: str) -> None:
        if not ch.isdigit():
            return
        sel = self._mask_selection_raw_range()
        raw = mask_raw(self.mask, self.value)
        capacity = mask_digit_count(self.mask)
        if sel is not None:
            start, end = sel
            available = capacity - (len(raw) - (end - start))
            if available <= 0:
                self._sel_anchor = None
                return
            self._save_history("type")
            self._mask_replace_raw_range(start, end, ch)
            self._sel_anchor = None
            return
        if len(raw) >= capacity:
            return  # complete -- refuse to write anything else
        self._save_history("type")
        idx = mask_raw_index_at(self.mask, self.cursor_pos)
        self._mask_replace_raw_range(idx, idx, ch)

    def _mask_backspace(self) -> None:
        sel = self._mask_selection_raw_range()
        if sel is not None:
            self._save_history("edit")
            self._mask_replace_raw_range(sel[0], sel[1], "")
            self._sel_anchor = None
            return
        idx = mask_raw_index_at(self.mask, self.cursor_pos)
        if idx <= 0:
            return
        self._save_history("backspace")
        self._mask_replace_raw_range(idx - 1, idx, "")

    def _mask_delete(self) -> None:
        sel = self._mask_selection_raw_range()
        if sel is not None:
            self._save_history("edit")
            self._mask_replace_raw_range(sel[0], sel[1], "")
            self._sel_anchor = None
            return
        raw = mask_raw(self.mask, self.value)
        idx = mask_raw_index_at(self.mask, self.cursor_pos)
        if idx >= len(raw):
            return
        self._save_history("delete")
        self._mask_replace_raw_range(idx, idx + 1, "")

    def _mask_paste(self, text: str) -> None:
        digits = "".join(c for c in text if c.isdigit())
        if not digits:
            return
        self._save_history("edit")
        sel = self._mask_selection_raw_range()
        raw = mask_raw(self.mask, self.value)
        capacity = mask_digit_count(self.mask)
        if sel is not None:
            start, end = sel
            remaining = capacity - (len(raw) - (end - start))
            self._mask_replace_raw_range(start, end, digits[: max(0, remaining)])
            self._sel_anchor = None
            return
        idx = mask_raw_index_at(self.mask, self.cursor_pos)
        remaining = capacity - len(raw)
        self._mask_replace_raw_range(idx, idx, digits[: max(0, remaining)])
