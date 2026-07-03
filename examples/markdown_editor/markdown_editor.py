import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Style
from cozy_tui.widgets import Box, Button, HBox, Label, MarkdownInput
from cozy_tui.events import Key
from cozy_tui.widget import Widget

# ── Sample ────────────────────────────────────────────────────────────────────

SAMPLE = """\
# Markdown Live Preview

**Tab** to preview · click **Edit** to return.

## Formatting

- **Bold**, *italic*, `inline code`
- Blockquotes, lists, headings, code blocks

> *Tab now to see this rendered!*
"""

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output.md")

# ── Status bar ────────────────────────────────────────────────────────────────


class StatusBar(Widget):
    """Renders live mode indicator and word/char counts on every frame."""

    def __init__(self, x, y, editor, width, style=None):
        super().__init__(x, y, style)
        self.editor = editor
        self._bar_width = width

    def natural_width(self, scale):
        return self._bar_width

    def draw(self, canvas):
        text = self.editor.value
        lines = text.count("\n") + 1 if text else 0
        words = len(text.split()) if text.strip() else 0
        chars = len(text)

        mode = "✎  EDITING" if canvas.focused is self.editor else "◉  PREVIEW"
        stats = f"Lines {lines}   Words {words}   Chars {chars}"

        w = self._bar_width
        gap = w - len(mode) - len(stats)
        bar = mode + " " * max(2, gap) + stats
        canvas.write(self.abs_x, self.abs_y, bar[:w].ljust(w), self.style)


# ── App & layout ──────────────────────────────────────────────────────────────

app = App(full=True, style=Style(fg="white", bg="black"))

W = 66  # editor column width

box = Box(
    2,
    1,
    "2100x720",
    border="rounded",
    style=Style(fg="cyan", bg="black"),
    title=" Markdown Editor ",
)

editor = MarkdownInput(
    2,
    2,
    W,
    multiline=True,
    placeholder="# Title\n\nStart writing **Markdown** here…",
    style=Style(fg="white"),
)
editor.value = SAMPLE
editor.cursor_pos = 0

box.add(editor)
box.add(Label(2, 3, "─" * W, style=Style(fg="cyan")))
box.add(StatusBar(2, 4, editor, W, style=Style(fg="bright_black")))

btn_row = HBox(2, 5, gap=2)
btn_edit = Button(0, 0, "Edit", width=10, style=Style(fg="white", bg="blue"))
btn_preview = Button(
    0, 0, "Preview", width=10, style=Style(fg="white", bg="bright_black")
)
btn_save = Button(0, 0, "Save", width=10, style=Style(fg="white", bg="green"))
btn_clear = Button(0, 0, "Clear", width=10, style=Style(fg="white", bg="magenta"))
btn_quit = Button(0, 0, "Quit", width=10, style=Style(fg="white", bg="red"))
btn_row.add(btn_edit).add(btn_preview).add(btn_save).add(btn_clear).add(btn_quit)
box.add(btn_row)

box.add(
    Label(
        2, 6, "Tab preview  •  Ctrl+S save  •  ESC quit", style=Style(fg="bright_black")
    )
)

# ── Callbacks ─────────────────────────────────────────────────────────────────


def _save(b=None):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(editor.value)


def _clear(b=None):
    editor.value = ""
    editor.cursor_pos = 0
    app.focus(editor)


btn_edit.on_click(lambda b: app.focus(editor))
btn_preview.on_click(lambda b: app.focus(btn_edit))
btn_save.on_click(_save)
btn_clear.on_click(_clear)
btn_quit.on_click(lambda b: app.quit())

app.on_key(Key.ESC, lambda: "quit")
app.on_key("\x13", _save)  # Ctrl+S

# ── Run ───────────────────────────────────────────────────────────────────────

app.add(box)
app.focus(editor)
app.run()
