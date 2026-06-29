# cozy_tui

A lightweight Python TUI (Terminal User Interface) library for Windows. Build keyboard-driven terminal apps with widgets, focus management, mouse support, and smooth cursor blinking — all rendered through raw VT sequences.

## Features

- **Widgets**: `Input`, `Label`, `Box` (with borders and titles)
- **Multi-line Input**: Shift+Enter to insert newlines, UP/DOWN to navigate lines
- **Focus system**: Tab / Shift+Tab to cycle focus, click to focus with mouse
- **Cursor blinking**: Uses the real terminal cursor — no character replacement, smooth blink
- **Mouse support**: Click to focus, scroll wheel to scroll
- **Scrolling**: Long content scrolls vertically; single-line inputs scroll horizontally
- **Keyboard shortcuts**: Register global handlers with `app.on_key()`

## Quick start

```python
from cozy_tui.app import App
from cozy_tui.style import Style
from cozy_tui.widgets.box import Box
from cozy_tui.widgets.input import Input
from cozy_tui.widgets.label import Label
from cozy_tui.events import Key

app = App(size=None, style=Style(fg="white", bg="black"), full=True)

box = Box(2, 1, "60x10", border="rounded", style=Style(fg="white", bg="black"), title="Demo")
box.add(Label(1, 1, "Name:"))
box.add(Input(7, 1, 20, placeholder="Enter your name"))
box.add(Label(1, 3, "Notes:"))
box.add(Input(7, 3, 20, placeholder="Shift+Enter for newline", multiline=True))
app.add(box)

app.on_key(Key.ESC, lambda: "quit")
app.run()
```

## Widgets

### `Input(x, y, width, placeholder="", style=None, cursor=True, cursor_style="vertical", flash=True, multiline=False)`

A text input field. Access the value with `.get()` or `.value`.

- `cursor_style`: `"vertical"` (default), `"block"`, or `"underline"`
- `multiline`: enables multi-line editing with Shift+Enter

### `Label(x, y, text, style=None)`

A static text label.

### `Box(x, y, size, text="", border="single", style=None, title="")`

A bordered container. Add children with `.add(widget)`.

Border styles: `"single"`, `"double"`, `"rounded"`, `"bold"`, `"none"`

## Key bindings

| Key | Action |
|-----|--------|
| Tab / Shift+Tab | Cycle focus |
| Arrow keys | Move cursor / navigate lines (Input) |
| Home / End | Jump to line start / end |
| Backspace / Delete | Delete character behind / ahead of cursor |
| Shift+Enter | Insert newline (multiline Input) |
| Ctrl+C | Quit |

## Requirements

- Python 3.10+
- Windows (uses `msvcrt` and Windows Console API)
