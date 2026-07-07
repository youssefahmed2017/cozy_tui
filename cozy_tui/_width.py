"""Terminal display-width of Unicode text.

The renderer works in fixed grid cells, so it must know how many columns a
character occupies: 0 for combining/zero-width marks, 2 for East-Asian wide and
most emoji, 1 otherwise. This is a compact `wcwidth`-style table — good enough
for labels, boxes, and CJK/emoji content without pulling in a dependency.
"""

from bisect import bisect_right

# Sorted, non-overlapping [start, end] ranges. `_boundaries` holds the flattened
# start/end+1 edges so a single bisect tells us whether a codepoint is inside.

_ZERO_WIDTH = [
    (0x0300, 0x036F),
    (0x0483, 0x0489),
    (0x0591, 0x05BD),
    (0x05BF, 0x05BF),
    (0x0610, 0x061A),
    (0x064B, 0x065F),
    (0x0670, 0x0670),
    (0x06D6, 0x06DC),
    (0x06DF, 0x06E4),
    (0x0711, 0x0711),
    (0x0730, 0x074A),
    (0x07A6, 0x07B0),
    (0x0900, 0x0903),
    (0x093A, 0x094F),
    (0x0951, 0x0957),
    (0x0E31, 0x0E31),
    (0x0E34, 0x0E3A),
    (0x0EB1, 0x0EB1),
    (0x0EB4, 0x0EBC),
    (0x1AB0, 0x1AFF),
    (0x1DC0, 0x1DFF),
    (0x200B, 0x200F),
    (0x202A, 0x202E),
    (0x2060, 0x2064),
    (0x20D0, 0x20FF),
    (0xFE00, 0xFE0F),
    (0xFE20, 0xFE2F),
    (0xFEFF, 0xFEFF),
]

_WIDE = [
    (0x1100, 0x115F),
    (0x2329, 0x232A),
    (0x2E80, 0x303E),
    (0x3041, 0x33FF),
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xA000, 0xA4CF),
    (0xAC00, 0xD7A3),
    (0xF900, 0xFAFF),
    (0xFE10, 0xFE19),
    (0xFE30, 0xFE6F),
    (0xFF00, 0xFF60),
    (0xFFE0, 0xFFE6),
    (0x1F300, 0x1F64F),
    (0x1F680, 0x1F6FF),  # Transport & Map Symbols (🚪 🚀 …)
    (0x1F900, 0x1F9FF),
    (0x1FA70, 0x1FAFF),  # Symbols & Pictographs Extended-A (🩹 🪑 …)
    (0x20000, 0x3FFFD),
]


def _flatten(ranges):
    edges = []
    for start, end in ranges:
        edges.append(start)
        edges.append(end + 1)
    return edges


_ZERO_EDGES = _flatten(_ZERO_WIDTH)
_WIDE_EDGES = _flatten(_WIDE)


def _in(edges, cp):
    # Odd insertion index => cp falls inside a [start, end] range.
    return bisect_right(edges, cp) & 1


def char_width(ch: str) -> int:
    """Return the column width (0, 1, or 2) of a single character."""
    cp = ord(ch)
    if cp == 0:
        return 0
    if cp < 32 or 0x7F <= cp < 0xA0:  # C0/C1 control chars are not printable
        return 0
    if cp < 0x300:  # below the lowest zero-width/wide codepoint (all Latin/ASCII)
        return 1
    if _in(_ZERO_EDGES, cp):
        return 0
    if _in(_WIDE_EDGES, cp):
        return 2
    return 1


def text_width(text: str) -> int:
    """Return the total column width of a string."""
    return sum(char_width(c) for c in text)


def clip_text(text: str, width: int) -> str:
    """Truncate `text` to fit within `width` columns, appending an ellipsis."""
    if text_width(text) <= width:
        return text
    out = ""
    for ch in text:
        if text_width(out + ch) > width - 1:
            break
        out += ch
    return out + "…"


def tail_clip_text(text: str, width: int) -> str:
    """Like `clip_text` but keeps the *end* of the text visible (e.g. a filename)."""
    if text_width(text) <= width:
        return text
    while text and text_width("…" + text) > width:
        text = text[1:]
    return "…" + text
