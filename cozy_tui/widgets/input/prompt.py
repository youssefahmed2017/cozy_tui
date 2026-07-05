from cozy_tui.events import Key
from cozy_tui.style import Style
from cozy_tui.widget import Widget


class PromptDialog(Widget):
    """A one-line text-entry panel, designed to be shown as a modal overlay via
    ``App.prompt()``. Enter fires ``on_submit(text)``; Esc / click-outside cancel
    (dismissal is handled by the overlay layer). Self-contained: it draws its own
    bordered panel, so it needs no surrounding ``Box``."""

    focusable = True

    def __init__(self, title, initial="", *, on_submit=None, width=40, style=None):
        super().__init__(0, 0, style or Style(fg="white", bg="black"))
        self.title = title
        self.text = initial
        self.on_submit = on_submit
        self.width = max(8, width)

    def natural_width(self, scale):
        return self.width + 2

    def natural_height(self, scale):
        return 5  # border(2) + title + input + hint

    def contains(self, col, row):
        return self.abs_x <= col < self.abs_x + self.natural_width(
            1
        ) and self.abs_y <= row < self.abs_y + self.natural_height(1)

    def on_key(self, key):
        if key == Key.ENTER:
            if self.on_submit is not None:
                self.on_submit(self.text)
        elif key == Key.BACKSPACE:
            self.text = self.text[:-1]
        elif isinstance(key, str) and len(key) == 1 and key.isprintable():
            self.text += key

    def _palette(self):
        raw_bg = self.style.raw_bg
        border = Style(fg="bright_cyan", bg=raw_bg, styles=["bold"])
        dim = Style(fg="bright_black", bg=raw_bg)
        return self.style, border, dim

    def draw(self, canvas):
        panel, border, dim = self._palette()
        x, y, w = self.abs_x, self.abs_y, self.width
        h = self.natural_height(1)
        canvas.write(x, y, "╭" + "─" * w + "╮", border)
        canvas.write(x, y + h - 1, "╰" + "─" * w + "╯", border)
        for i in range(h - 2):
            canvas.write(x, y + 1 + i, "│", border)
            canvas.write(x + 1, y + 1 + i, " " * w, panel)
            canvas.write(x + w + 1, y + 1 + i, "│", border)
        canvas.write(x + 1, y + 1, (" " + self.title).ljust(w)[:w], border)
        line = "> " + self.text
        line = line[-(w - 2) :] if len(line) > w - 2 else line
        canvas.write(x + 1, y + 2, (" " + line + "▏").ljust(w)[:w], panel)
        canvas.write(x + 1, y + 3, "  Enter: save    Esc: cancel".ljust(w)[:w], dim)
