"""Fixed/simple tank contents that aren't Fish: dropped Food, foraged Wood,
the Forest's prowling Tiger Shark, and furniture Decoration widgets."""

import time

from cozy_tui import Style
from cozy_tui._width import text_width
from cozy_tui.widget import Widget

from .constants import DECORATION_SELL_MULT
from .styles import FOOD_STYLE, TIGER_SHARK_STYLE, WOOD_STYLE


class Food(Widget):
    """A bite of food sitting in the tank for fish to eat. Plain food (the
    default) is a "•" pellet; a *special* food (a treat dropped into the
    water, e.g. Pizza -- see aquarium.py's _drop_special_food()) carries its
    own `kind`, emoji `glyph`, and an `on_eaten(eater)` hook the eating fish
    calls so the treat's reaction (favorite-food delight, Pizza's universal
    craving, ...) fires the same way feeding it via the Inspector would."""

    GLYPH = "•"

    def __init__(self, x: float, y: float, *, glyph: str = None, style=None, kind=None):
        super().__init__(round(x), round(y), style or FOOD_STYLE)
        self.fx, self.fy = float(x), float(y)
        self.glyph = glyph or self.GLYPH
        self.kind = kind  # None for plain food; a TREAT_SHOP_ITEMS kind otherwise
        self.on_eaten = None  # set to on_eaten(eater) for a special food

    def natural_width(self, scale) -> int:
        return 1

    def natural_height(self, scale) -> int:
        return 1

    def draw(self, canvas) -> None:
        canvas.write(self.abs_x, self.abs_y, self.glyph, self.style)


class Wood(Widget):
    """A piece of Wood sitting in the Forest scene, waiting to be foraged
    (see aquarium.py's _check_foraging()) -- same shape as Food, just a
    different glyph/style and a different biome. Purely a static pickup:
    nothing steers toward it visually in this slice (foraging is
    timer-driven, not real steering -- see the Exploration Update Slice 1
    plan), so this class only ever needs to exist and draw itself."""

    GLYPH = "🪵"  # plain ASCII (like Food's "•") so WOOD_STYLE actually tints it

    def __init__(self, x: float, y: float):
        super().__init__(round(x), round(y), WOOD_STYLE)
        self.fx, self.fy = float(x), float(y)

    def natural_width(self, scale) -> int:
        return 1

    def natural_height(self, scale) -> int:
        return 1

    def draw(self, canvas) -> None:
        canvas.write(self.abs_x, self.abs_y, self.GLYPH, self.style)


class TigerShark(Widget):
    """The predator that prowls the Forest during a forage-danger event
    (see aquarium.py's _check_forest_danger()). Unlike the tank's own Shark
    (a full Fish with hunting AI), this one never eats -- its whole job is
    to be a scare that sends foraging fish fleeing home, dropping any wood
    they were carrying; everyone survives. It just swims steadily across the
    scene from the side it entered on while it's present; its lifecycle
    (appear, linger, leave) is driven entirely by that per-second check,
    same as every other Forest object -- this class only animates its own
    horizontal drift so the swim reads as motion rather than a teleport.

    `vx` (cells/second, signed) sets both the swim direction and which way
    it faces. `paused` is the same zero-arg-callable shared-mutable pattern
    LeafField/Fish already use, so it freezes mid-swim when the game is
    paused rather than jumping ahead on resume."""

    ART_RIGHT = "▶≡≡≡≡>"
    ART_LEFT = "<≡≡≡≡◀"

    def __init__(self, x: float, y: float, vx: float, paused=lambda: False):
        super().__init__(round(x), round(y), TIGER_SHARK_STYLE)
        self.fx, self.fy = float(x), float(y)
        self.vx = vx
        self._paused = paused
        self._last = time.monotonic()

    @property
    def _glyph(self) -> str:
        return self.ART_RIGHT if self.vx >= 0 else self.ART_LEFT

    def natural_width(self, scale) -> int:
        return text_width(self._glyph)

    def natural_height(self, scale) -> int:
        return 1

    def draw(self, canvas) -> None:
        now = time.monotonic()
        dt = now - self._last
        self._last = now
        if not self._paused():
            self.fx += self.vx * dt
            self.x, self.y = round(self.fx), round(self.fy)
        canvas.write(self.abs_x, self.abs_y, self._glyph, self.style)


class Decoration(Widget):
    """A fixed piece of tank furniture (Plant/Rock/Castle/Driftwood). Never
    moves and is never eaten -- Fish just steer away from it (see
    avoid_decorations()), or toward it if it's their favorite spot (see
    Fish.favorite_decoration). `color` is either one color for every row of
    `art`, or a list matching len(art) for a little per-part shading. `kind`
    is the plain display name shown in the Inspector's "Favorite spot" line.

    `capacity` (Phase 7) is the only thing that makes a decoration a
    "container" fish can sleep inside overnight (see Fish._claim_home()) --
    0 (the default, and every non-container kind's value) means it isn't
    one. No separate ContainerDecoration subclass: a plain attribute is
    simpler and means any future decoration becomes a home just by picking
    a nonzero capacity in DECORATION_SHOP_ITEMS, no new class required."""

    def __init__(
        self,
        x: float,
        y: float,
        art: list[str],
        color,
        kind: str = "Decoration",
        price: int = 0,
        capacity: int = 0,
    ):
        colors = [color] * len(art) if isinstance(color, str) else list(color)
        super().__init__(round(x), round(y), Style(fg=colors[0]))
        self.art = art
        self.row_styles = [Style(fg=c) for c in colors]
        self.kind = kind
        self.price = price  # this kind's Shop price -- sell_value is a fraction of it
        self.capacity = capacity
        self.fx, self.fy = float(x), float(y)
        w = max(text_width(line) for line in art)
        h = len(art)
        self.radius = max(w, h) / 2

    @property
    def is_container(self) -> bool:
        return self.capacity > 0

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
