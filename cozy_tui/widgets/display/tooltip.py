from cozy_tui._width import text_width
from cozy_tui.style import Style
from cozy_tui.widget import Widget


class Tooltip(Widget):
    """A small floating one-line text bubble, shown as a non-modal overlay
    anchored to another widget. Non-focusable and purely visual -- like
    :class:`~cozy_tui.widgets.Toast`, it never steals focus or blocks input,
    so whatever's under it stays fully interactive while it's showing.

    Usually created via ``App.set_tooltip(widget, text)`` rather than
    directly -- that handles the hover wiring, the show delay, and hiding it
    again. Position is recomputed every frame from ``anchor``'s current
    ``abs_x``/``abs_y`` (right below it, flipped above/left if that would run
    off the screen edge), so it tracks a moving or resizing anchor correctly.
    """

    def __init__(self, anchor, text: str, *, style=None):
        super().__init__(
            0, 0, style or Style(fg="black", bg="bright_yellow"), name="Tooltip"
        )
        self.anchor = anchor
        self.text = text

    def natural_width(self, scale) -> int:
        return text_width(self.text) + 2  # 1 pad each side

    def natural_height(self, scale) -> int:
        return 1

    def _position(self, canvas) -> None:
        w = self.natural_width(1)
        x = self.anchor.abs_x
        y = self.anchor.abs_y + max(1, self.anchor.natural_height(canvas.SCALE))
        if x + w > canvas.cols:
            x = max(0, canvas.cols - w)
        if y >= canvas.rows:
            y = max(0, self.anchor.abs_y - 1)  # no room below -- show above instead
        self.x, self.y = x, y

    def draw(self, canvas) -> None:
        self._position(canvas)
        canvas.write(self.abs_x, self.abs_y, f" {self.text} ", self.style)
