"""MarkdownInput: Input with live Rich Markdown preview when not focused."""

from __future__ import annotations

from cozy_tui.widgets.display.markdown import Markdown
from cozy_tui.widgets.input.input import Input


class MarkdownInput(Input, Markdown):
    """Input widget that renders its content as a live Markdown preview when unfocused.

    - focused   → raw text with cursor  (standard Input rendering)
    - unfocused → Rich Markdown preview (Markdown rendering)

    All editing behavior is inherited from Input unchanged. Requires ``rich``.

    MRO: MarkdownInput → Input → … mixins … → Markdown → Widget
    Input's ``value``, ``width``, ``placeholder``, and ``_placeholder_style``
    shadow Markdown's equivalents, so editing semantics are never disrupted.
    """

    def __init__(self, *args, **kwargs):
        Input.__init__(self, *args, **kwargs)
        self._md_cache_key = None
        self._md_lines = None
        self.laps = True

    def draw(self, canvas) -> None:
        if canvas.focused is self:
            Input.draw(self, canvas)
        else:
            self._draw_markdown(canvas)

    def natural_height(self, scale: int) -> int:
        input_h = Input.natural_height(self, scale)
        if self.value:
            w = self._clip_width or self.width
            rich_h = max(1, len(self._rendered_lines(w)))
            return max(input_h, rich_h)
        return input_h
