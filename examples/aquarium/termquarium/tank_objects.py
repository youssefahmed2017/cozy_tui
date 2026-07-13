"""Fixed/simple tank contents that aren't Fish: dropped Food and furniture
Decoration widgets."""

from cozy_tui import Style
from cozy_tui._width import text_width
from cozy_tui.widget import Widget

from .constants import DECORATION_SELL_MULT
from .styles import FOOD_STYLE


class Food(Widget):
    GLYPH = "•"

    def __init__(self, x: float, y: float):
        super().__init__(round(x), round(y), FOOD_STYLE, name="Food")
        self.fx, self.fy = float(x), float(y)

    def natural_width(self, scale) -> int:
        return 1

    def natural_height(self, scale) -> int:
        return 1

    def draw(self, canvas) -> None:
        canvas.write(self.abs_x, self.abs_y, self.GLYPH, self.style)


class Decoration(Widget):
    """A fixed piece of tank furniture (Plant/Rock/Castle/Driftwood). Never
    moves and is never eaten -- Fish just steer away from it (see
    avoid_decorations()), or toward it if it's their favorite spot (see
    Fish.favorite_decoration). `color` is either one color for every row of
    `art`, or a list matching len(art) for a little per-part shading. `kind`
    is the plain display name shown in the Inspector's "Favorite spot" line."""

    def __init__(
        self,
        x: float,
        y: float,
        art: list[str],
        color,
        kind: str = "Decoration",
        price: int = 0,
    ):
        colors = [color] * len(art) if isinstance(color, str) else list(color)
        super().__init__(round(x), round(y), Style(fg=colors[0]), name="Decoration")
        self.art = art
        self.row_styles = [Style(fg=c) for c in colors]
        self.kind = kind
        self.price = price  # this kind's Shop price -- sell_value is a fraction of it
        self.fx, self.fy = float(x), float(y)
        w = max(text_width(line) for line in art)
        h = len(art)
        self.radius = max(w, h) / 2

    @property
    def sell_value(self) -> int:
        return round(self.price * DECORATION_SELL_MULT)

    def natural_width(self, scale) -> int:
        return max(text_width(line) for line in self.art)

    def natural_height(self, scale) -> int:
        return len(self.art)

    def draw(self, canvas) -> None:
        for i, line in enumerate(self.art):
            canvas.write(self.abs_x, self.abs_y + i, line, self.row_styles[i])


def decoration_at(decorations, col: int, row: int):
    """The Decoration in `decorations` covering (col, row), or None -- a
    Decoration is static (unlike Fish, its x/y never change after
    construction) and can span multiple rows/cols, so this checks a full
    rectangle rather than fish_at()'s single-row check."""
    for d in decorations:
        w, h = d.natural_width(1), d.natural_height(1)
        if d.y <= row < d.y + h and d.x <= col < d.x + w:
            return d
    return None
