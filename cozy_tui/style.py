import sys

sys.stdout.reconfigure(encoding="utf-8")


class Style:
    __slots__ = ("fg", "bg", "styles")

    def __init__(self, fg=None, bg=None, styles=None):
        self.fg = fg
        if bg and not bg.startswith("rgb("):
            self.bg = f"{bg}_bg"
        else:
            self.bg = bg  # None or "rgb(R,G,B)" — no suffix needed
        self.styles = tuple(styles) if styles else ()


class Cell:
    __slots__ = ("char", "style")

    def __init__(self, char: str, style: Style) -> None:
        self.char = char
        self.style = style
