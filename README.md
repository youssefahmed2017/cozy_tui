# cozy_tui

[![CI (Windows · macOS · Linux)](https://github.com/youssefahmed2017/cozy_tui/actions/workflows/ci.yml/badge.svg)](https://github.com/youssefahmed2017/cozy_tui/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/cozy-tui.svg)](https://pypi.org/project/cozy-tui/)
[![Python versions](https://img.shields.io/pypi/pyversions/cozy-tui.svg)](https://pypi.org/project/cozy-tui/)
[![GitHub stars](https://img.shields.io/github/stars/youssefahmed2017/cozy_tui.svg)](https://github.com/youssefahmed2017/cozy_tui/stargazers)

A lightweight, cross-platform Python TUI (Terminal User Interface) library. Build keyboard-driven terminal apps with widgets, focus management, mouse support, and smooth cursor blinking — all rendered through raw VT sequences. Runs on Windows (Console API) and POSIX (Linux/macOS via `termios`).

---

## Documentation

Full documentation lives in [`docs/`](https://github.com/youssefahmed2017/cozy_tui/tree/master/docs) (GitHub) directory:

- **[Core Concepts](https://github.com/youssefahmed2017/cozy_tui/blob/master/docs/concepts.md)** — the render loop, coordinate system, and widget lifecycle.
- **[Widgets](https://github.com/youssefahmed2017/cozy_tui/blob/master/docs/widgets.md)** — every widget: `App`, `Box`, `Label`, `Hyperlink`, `Bindings`, `Text`, `Input`, `Button`, `Checkbox`, `Slider`, `MarkdownInput`, `DropFilesArea`, `ListView`, `CheckList`, `RadioSet`, `RightClickMenu`, `MenuBar`, `Dropdown`, `ProgressBar`, `Spinner`, `Toast`, `Tooltip`, `Table`, `Tabs`, `ScrollView`, `Splitter`, `Collapsible`, `Tree`, `AnimatedLabel`, `TracebackView`.
- **[Layouts, Dock & Overlays](https://github.com/youssefahmed2017/cozy_tui/blob/master/docs/layouts.md)** — `VBox`/`HBox`/`Grid`, `app.dock(...)`, and the overlay/modal layer (`open_overlay`, `app.prompt`, `app.confirm`, `app.pick_file`).
- **[Styling](https://github.com/youssefahmed2017/cozy_tui/blob/master/docs/styling.md)** — `Style`, colors, text attributes, and `Theme`s.
- **[Input & Interaction](https://github.com/youssefahmed2017/cozy_tui/blob/master/docs/interaction.md)** — key bindings, mouse support, focus, scrolling, and the Ctrl+P command palette.
- **[Examples](https://github.com/youssefahmed2017/cozy_tui/blob/master/docs/examples.md)** — runnable demos in [`examples/`](examples).

---

## Features

- **Cross-platform** — runs on Windows (Console API) and POSIX (Linux/macOS via `termios`); the backend is chosen automatically.
- **Very few dependencies** — the clipboard is built in (no `pyperclip`); the only third-party dependency is `rich`, used to render `Markdown`/`MarkdownInput` and to syntax-highlight `TracebackView`/`show_traceback`. Everything else is the standard library.
- **Built-in clipboard** — `cozy_tui.clipboard.copy`/`paste` with native backends per platform (Win32 API, `pbcopy`/`pbpaste`, `wl-clipboard`/`xclip`/`xsel`, or OSC 52 fallback).
- **Unicode-aware rendering** — a built-in `wcwidth`-style width layer keeps CJK/emoji (double-width) and combining marks (zero-width) aligned in the cell grid.
- **Widgets**: `Button`, `Checkbox`, `Input`, `Slider`, `Label`, `Hyperlink`, `Bindings`, `AnimatedLabel`, `Text`, `Box`, `MarkdownInput`, `DropFilesArea`, `ListView`, `CheckList`, `RadioSet`, `RightClickMenu`, `MenuBar`, `Dropdown`, `ProgressBar`, `Spinner`, `Toast`, `Tooltip`, `Table`, `Tabs`, `ScrollView`, `Splitter`, `Collapsible`, `Tree`, `TracebackView`
- **Themes**: a `Theme` bundles the accent/muted/semantic/selection colors most widgets and `app.toast(...)` draw from; switch with `set_theme(theme)`/`theme.activate()`, or interactively via the Ctrl+T searchable picker (over 20 built-in presets in `Theme.MODES`) — see [styling.md](https://github.com/youssefahmed2017/cozy_tui/blob/master/docs/styling.md#themes)
- **Command palette**: Ctrl+P opens a Textual-style searchable list of commands (`app.register_command(...)` to add your own) — Quit, Change Theme, and Keys (a live keybindings legend) are built in
- **Crash screens**: unhandled exceptions in `app.run()` automatically show a full-screen, scrollable, syntax-highlighted `TracebackView` with one-key clipboard copy (`App(catch_errors=False)` to get a plain propagating exception instead); call `cozy_tui.crash_screen.show_traceback(exc)` directly to get the same screen outside of `run()`
- **Context menus**: `RightClickMenu` with icons, shortcut labels, and submenus — pop it up from `app.on_right_click(...)`; `MenuBar` docks the same building blocks to the top of the screen as a File/Edit-style menu bar
- **Layouts**: `VBox`, `HBox`, `Grid` — auto-position children without manual x/y, with `flex=` to grow docked children into leftover space; `Splitter` for a user-resizable two-pane divider
- **Dock layout**: `app.dock(widget, "top"/"bottom"/"left"/"right"/"fill")` — edge-anchored regions that re-flow on resize
- **Overlays & modals**: `app.open_overlay(widget)` floats a widget above the UI, dims the background, and confines focus/input — the basis for dialogs (`app.prompt`, `app.confirm`, `app.pick_file`), menus, and tooltips (`app.set_tooltip`)
- **Input validation**: `Input(inp_type="number")` filters keystrokes to valid numbers as you type; `required=`/`validator=` plus `.error`/`.is_valid` for anything else, with automatic error-color styling
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

That's it — `rich` (used to render `Markdown`/`MarkdownInput` and to syntax-highlight `TracebackView`) is pulled in automatically.

Take it for a spin with the built-in demo:

```bash
cozy-tui              # or: python -m cozy_tui
```

### Command-line

Installing the package also provides a `cozy-tui` command (equivalently `python -m cozy_tui`):

```bash
cozy-tui              # launch the interactive demo (no subcommand)
cozy-tui demo         # launch the interactive demo
cozy-tui --version    # print the installed version
cozy-tui doctor       # check Python, imports, clipboard backend, color depth, PyPI version
cozy-tui doctor --offline   # skip the PyPI check
cozy-tui info         # version + detected terminal capabilities
cozy-tui run script.py           # run a script, like `python script.py`
cozy-tui run --debug script.py   # ...with App(debug=True) on, no code change needed
```

Then in your script:

```python
from cozy_tui import App, Style
from cozy_tui.widgets import Box, Label, Input, Button
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
from cozy_tui import App, Style
from cozy_tui.widgets import Box, Label, Input, Button, Checkbox
from cozy_tui.events import Key

app = App(full=True, size=None, style=Style(fg="white", bg="black"))

# Box size = virtual pixels ÷ App.SCALE (10) → "600x140" = 60 cols × 14 rows
box = Box(2, 1, "600x140", border="rounded", style=Style(fg="white", bg="black"), title="Sign Up")

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
