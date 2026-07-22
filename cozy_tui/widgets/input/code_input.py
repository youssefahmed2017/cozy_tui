"""CodeInput: Input with live syntax highlighting when not focused."""

from __future__ import annotations

from cozy_tui.widgets.display.code import DEFAULT_THEME, Code
from cozy_tui.widgets.input.input import Input


class CodeInput(Input, Code):
    """An editable code field that renders as a highlighted :class:`Code` block
    whenever it isn't focused.

    - focused   → raw text with cursor, selection, and scrolling (plain Input)
    - unfocused → Rich/Pygments syntax highlighting (Code rendering)

    Exactly the split :class:`~cozy_tui.widgets.MarkdownInput` uses, for the
    same reason: full editing fidelity is worth more than color *while you are
    typing*, and highlighting is worth more than a bare cursor the rest of the
    time. Editing behavior is inherited from ``Input`` unchanged.

    ::

        editor = CodeInput(2, 1, 40, lang="python")
        editor.value = 'print("hi")'

    MRO: CodeInput → Input → … mixins … → Code → Widget. ``Input``'s ``value``,
    ``width``, and ``draw`` shadow ``Code``'s, so editing semantics are never
    disrupted; ``code`` below is what points ``Code``'s renderer back at the
    text ``Input`` is actually editing.
    """

    def __init__(
        self,
        x,
        y,
        width,
        *,
        lang: str = "python",
        theme: str = DEFAULT_THEME,
        line_numbers: bool = False,
        background: bool = True,
        tab_size: int = 4,
        multiline: bool = True,
        **kwargs,
    ):
        # Only Input.__init__ runs -- Code.__init__ would try to assign `code`,
        # which is a read-only view onto Input's `value` here. Code's render
        # state is set up by hand instead, the same way MarkdownInput seeds its
        # own cache fields.
        Input.__init__(self, x, y, width, multiline=multiline, **kwargs)
        self.lang = lang
        self.theme = theme
        self.line_numbers = line_numbers
        self.background = background
        self.tab_size = tab_size
        self._cache_key = None
        self._rows = None
        self._measured = None
        self.laps = True

    @property
    def code(self) -> str:
        """The text being edited. Read-only: assign :attr:`value` instead --
        this exists so ``Code``'s renderer (and its cache key) follow the
        ``Input`` half of this widget rather than a second copy of the text."""
        return self.value

    def draw(self, canvas) -> None:
        if canvas.focused is self:
            Input.draw(self, canvas)
        else:
            Code.draw(self, canvas)

    def natural_height(self, scale: int) -> int:
        input_h = Input.natural_height(self, scale)
        if self.value:
            return max(input_h, Code.natural_height(self, scale))
        return input_h
