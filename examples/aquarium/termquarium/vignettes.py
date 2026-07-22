"""In-tank visual half of the morning vignette (see relationships.
choose_morning_vignette()) -- the toast is the narrative headline, this is
the cute moment played out where the two fish actually are."""

import time

from cozy_tui.widget import Widget

from .constants import MORNING_VIGNETTE_FRAME_SECONDS


class MorningVignette(Widget):
    """A short, self-removing 2-line caption: *boop* over a sleepy glyph for
    MORNING_VIGNETTE_FRAME_SECONDS, then either *awake* (`wakes=True`) or
    *...zzz* (`wakes=False` -- a Sleepy fish resisting the boop, see
    choose_morning_vignette()) over the pair's own glyphs for another
    MORNING_VIGNETTE_FRAME_SECONDS, then it's done -- the caller (main())
    removes it from app.widgets once total_seconds has elapsed. Purely
    decorative: it doesn't touch either Fish, which are already awake (or,
    for a resisting Sleepy fish, still genuinely asleep) by the time this
    fires -- see choose_morning_vignette()'s docstring for why."""

    def __init__(self, x, y, glyph_a, glyph_b, style, wakes: bool = True):
        super().__init__(round(x), round(y), style)
        self.glyph_a = glyph_a
        self.glyph_b = glyph_b
        self.wakes = wakes
        self._start = time.monotonic()

    @property
    def total_seconds(self) -> float:
        return MORNING_VIGNETTE_FRAME_SECONDS * 2

    def natural_width(self, scale) -> int:
        return 14

    def natural_height(self, scale) -> int:
        return 2

    def draw(self, canvas) -> None:
        elapsed = time.monotonic() - self._start
        if elapsed < MORNING_VIGNETTE_FRAME_SECONDS:
            caption = "*boop* 😴"
        elif self.wakes:
            caption = "*awake* 🙂"
        else:
            caption = "*...zzz* 😴"
        canvas.write(self.abs_x, self.abs_y, caption, self.style)
        canvas.write(
            self.abs_x, self.abs_y + 1, f"{self.glyph_a}    {self.glyph_b}", self.style
        )
