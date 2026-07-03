import webbrowser

from cozy_tui._width import text_width
from cozy_tui.events import Key
from cozy_tui.style import Style
from cozy_tui.widget import Widget


class Hyperlink(Widget):
    """A clickable text link. When focused, Enter or Space opens ``link`` in the
    default web browser; a mouse click opens it directly. Renders like a `Label`
    (blue, bold, underlined by default) and highlights while focused."""

    focusable = True

    def __init__(self, x, y, text, link, style=None):
        super().__init__(x, y, style or Style(fg="blue", styles=["bold", "underline"]))
        self.text = text
        self.link = link
        self.laps = True

    def _open(self) -> None:
        webbrowser.open(self.link)

    def natural_width(self, scale) -> int:
        return text_width(self.text)

    def natural_height(self, scale) -> int:
        if self._clip_width and self.text:
            return max(1, (len(self.text) + self._clip_width - 1) // self._clip_width)
        return 1

    def contains(self, col: int, row: int) -> bool:
        return self.abs_y == row and self.abs_x <= col < self.abs_x + text_width(
            self.text
        )

    def on_key(self, key) -> None:
        if key in (Key.ENTER, " "):
            self._open()

    def on_mouse_click(self, col=None, row=None) -> None:
        self._open()

    def draw(self, canvas) -> None:
        style = self.style
        if canvas.focused is self:
            # Invert onto the link colour so the focused link stands out.
            style = Style(fg="black", bg=style.fg or "blue", styles=style.styles)
        if self._clip_width:
            w = self._clip_width
            for i in range(0, max(1, len(self.text)), w):
                canvas.write(
                    self.abs_x, self.abs_y + i // w, self.text[i : i + w], style
                )
        else:
            canvas.write(self.abs_x, self.abs_y, self.text, style)
