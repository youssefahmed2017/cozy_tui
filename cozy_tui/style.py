import sys

sys.stdout.reconfigure(encoding="utf-8")

from cozy_kit import TextCustomizations

tc = TextCustomizations()


class Style:
    def __init__(
        self,
        fg=None,
        bg=None,
        styles=None,
    ):
        self.fg = fg
        self.bg = f"{bg}_bg" if bg else None
        self.styles = styles or []


class Cell:
    def __init__(self, char: str, style: Style) -> None:
        self.char = char
        self.style = style

    def render(self):
        args = []

        if self.style.bg:
            args.append(self.style.bg)

        if self.style.fg:
            args.append(self.style.fg)

        args.extend(self.style.styles)

        return tc.customize(self.char, *args)
