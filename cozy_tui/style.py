import sys

sys.stdout.reconfigure(encoding="utf-8")


class Style:
    __slots__ = ("fg", "bg", "styles")

    def __init__(self, fg=None, bg=None, styles=None):
        self.fg = fg
        self.bg = f"{bg}_bg" if bg else None
        self.styles = tuple(styles) if styles else ()


class Cell:
    __slots__ = ("char", "style")

    def __init__(self, char: str, style: Style) -> None:
        self.char = char
        self.style = style
