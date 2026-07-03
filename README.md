# cozy_tui

[![CI (Windows · macOS · Linux)](https://github.com/youssefahmed2017/cozy_tui/actions/workflows/ci.yml/badge.svg)](https://github.com/youssefahmed2017/cozy_tui/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/cozy-tui.svg)](https://pypi.org/project/cozy-tui/)
[![Python versions](https://img.shields.io/pypi/pyversions/cozy-tui.svg)](https://pypi.org/project/cozy-tui/)
[![GitHub stars](https://img.shields.io/github/stars/youssefahmed2017/cozy_tui.svg)](https://github.com/youssefahmed2017/cozy_tui/stargazers)

A lightweight, cross-platform Python TUI (Terminal User Interface) library. Build keyboard-driven terminal apps with widgets, focus management, mouse support, and smooth cursor blinking — all rendered through raw VT sequences. Runs on Windows (Console API) and POSIX (Linux/macOS via `termios`).

---

## Documentation

Full documentation lives in [`docs/`](docs):

- **[Core Concepts](docs/concepts.md)** — the render loop, coordinate system, and widget lifecycle.
- **[Widgets](docs/widgets.md)** — every widget: `App`, `Box`, `Label`, `Hyperlink`, `Bindings`, `Text`, `Input`, `Button`, `Checkbox`, `MarkdownInput`, `ListView`, `CheckList`, `Dropdown`, `ProgressBar`, `Table`, `Collapsible`, `Tree`, `AnimatedLabel`.
- **[Layouts, Dock & Overlays](docs/layouts.md)** — `VBox`/`HBox`/`Grid`, `app.dock(...)`, and the overlay/modal layer (`open_overlay`, `app.prompt`).
- **[Styling](docs/styling.md)** — `Style`, colors, and text attributes.
- **[Input & Interaction](docs/interaction.md)** — key bindings, mouse support, focus, and scrolling.
- **[Examples](docs/examples.md)** — runnable demos in [`examples/`](examples).

---

## Features

- **Cross-platform** — runs on Windows (Console API) and POSIX (Linux/macOS via `termios`); the backend is chosen automatically.
- **Very few dependencies** — the clipboard is built in (no `pyperclip`); the only third-party dependency is `rich`, used to render `Markdown`/`MarkdownInput`. Everything else is the standard library.
- **Built-in clipboard** — `cozy_tui.clipboard.copy`/`paste` with native backends per platform (Win32 API, `pbcopy`/`pbpaste`, `wl-clipboard`/`xclip`/`xsel`, or OSC 52 fallback).
- **Unicode-aware rendering** — a built-in `wcwidth`-style width layer keeps CJK/emoji (double-width) and combining marks (zero-width) aligned in the cell grid.
- **Widgets**: `Button`, `Checkbox`, `Input`, `Label`, `Hyperlink`, `Bindings`, `AnimatedLabel`, `Text`, `Box`, `MarkdownInput`, `ListView`, `CheckList`, `Dropdown`, `ProgressBar`, `Table`, `Collapsible`, `Tree`
- **Layouts**: `VBox`, `HBox`, `Grid` — auto-position children without manual x/y
- **Dock layout**: `app.dock(widget, "top"/"bottom"/"left"/"right"/"fill")` — edge-anchored regions that re-flow on resize
- **Overlays & modals**: `app.open_overlay(widget)` floats a widget above the UI, dims the background, and confines focus/input — the basis for dialogs, menus, and tooltips
- **Multi-line Input**: Enter or Shift+Enter to insert newlines, UP/DOWN to navigate lines
- **Markdown preview**: `MarkdownInput` renders live Rich Markdown when unfocused
- **Focus system**: Tab / Shift+Tab to cycle focus, click to focus with mouse
- **Cursor blinking**: Uses the real terminal cursor — smooth blink with no character replacement
- **Mouse support**: Click to focus widgets, click to activate buttons, scroll wheel to scroll
- **Scrolling**: Long content scrolls vertically; single-line inputs scroll horizontally
- **Global key handlers**: Register app-wide shortcuts with `app.on_key()`
- **Flexible styling**: Per-widget foreground, background, and text styles (bold, dim, underline)

---

---

## Requirements

- Python 3.10+
- A VT-capable terminal on **Windows** (Windows Console API) or **POSIX** (Linux/macOS, via `termios`/`tty`). The console backend is selected automatically at import.

---

---

## Installation

```bash
pip install cozy-tui
```

That's it — `rich` (used to render `Markdown` / `MarkdownInput`) is pulled in automatically.

Take it for a spin with the built-in demo:

```bash
python -m cozy_tui
```

Then in your script:

```python
from cozy_tui import App, Box, Label, Input, Button, Style
```

### From source (for development)

```bash
git clone https://github.com/youssefahmed2017/cozy_tui.git
cd cozy_tui
pip install -e .            # add [dev] for the test suite (pytest)
```

---

---

## Quick Start

```python
from cozy_tui import App, Box, Label, Input, Button, Checkbox, Style
from cozy_tui.events import Key

app = App(full=True, size=None, style=Style(fg="white", bg="black"))

# Box size = virtual pixels ÷ 30 → "1800x420" = 60 cols × 14 rows
box = Box(2, 1, "1800x420", border="rounded", style=Style(fg="white", bg="black"), title="Sign Up")

box.add(Label(2, 2, "Username:"))
box.add(Input(12, 2, 20, placeholder="Enter username"))

box.add(Label(2, 4, "Bio:"))
box.add(Input(12, 4, 20, placeholder="Tell us about you", multiline=True))

box.add(Checkbox(2, 7, "Subscribe to newsletter"))
box.add(Checkbox(2, 9, "I agree to the terms", checked=True))

btn = Button(2, 11, "Submit", width=20, style=Style(fg="white", bg="blue"))
btn.on_click(lambda b: print("Submitted!"))
box.add(btn)

app.add(box)
app.focus(btn)
app.on_key(Key.ESC, lambda: "quit")
app.run()
```

---
