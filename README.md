# cozy_tui

A lightweight Python TUI (Terminal User Interface) library for Windows. Build keyboard-driven terminal apps with widgets, focus management, mouse support, and smooth cursor blinking — all rendered through raw VT sequences.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Widgets](#widgets)
  - [App](#app)
  - [Box](#box)
  - [Label](#label)
  - [Input](#input)
  - [Button](#button)
  - [Checkbox](#checkbox)
  - [MarkdownInput](#markdowninput)
  - [ListView / ListItem](#listview--listitem)
  - [Dropdown](#dropdown)
  - [ProgressBar](#progressbar)
- [Layouts](#layouts)
  - [Layout (base)](#layout-base)
  - [VBox](#vbox)
  - [HBox](#hbox)
  - [Grid](#grid)
- [Styling](#styling)
- [Key Bindings](#key-bindings)
- [Mouse Support](#mouse-support)
- [Focus System](#focus-system)
- [Scrolling](#scrolling)
- [Examples](#examples)

---

## Features

- **Very few dependencies** — almost pure Python, uses only two dependencies, `cozy-kit` and `pyperclip`, everything else is the standard library.
- **Widgets**: `Button`, `Checkbox`, `Input`, `Label`, `Box`, `MarkdownInput`, `ListView`, `Dropdown`, `ProgressBar`
- **Layouts**: `VBox`, `HBox`, `Grid` — auto-position children without manual x/y
- **Multi-line Input**: Enter or Shift+Enter to insert newlines, UP/DOWN to navigate lines
- **Markdown preview**: `MarkdownInput` renders live Rich Markdown when unfocused
- **Focus system**: Tab / Shift+Tab to cycle focus, click to focus with mouse
- **Cursor blinking**: Uses the real terminal cursor — smooth blink with no character replacement
- **Mouse support**: Click to focus widgets, click to activate buttons, scroll wheel to scroll
- **Scrolling**: Long content scrolls vertically; single-line inputs scroll horizontally
- **Global key handlers**: Register app-wide shortcuts with `app.on_key()`
- **Flexible styling**: Per-widget foreground, background, and text styles (bold, dim, underline)

---

## Requirements

- Python 3.10+
- Windows (uses `msvcrt` and the Windows Console API for raw input mode)

---

## Installation

Clone the repo and import directly — no package installation needed:

```bash
git clone https://github.com/youssefahmed2017/cozy_tui.git
```

Then in your script:

```python
from cozy_tui import App, Box, Label, Input, Button, Style
```

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

## Core Concepts

### How rendering works

`cozy_tui` maintains an in-memory grid of cells (one per terminal character). Every frame, each widget writes its content into this grid via `canvas.write(x, y, text, style)`. After all widgets have drawn, the grid is serialized into ANSI escape sequences and written to stdout in one shot — this prevents flickering.

### Coordinate system

All positions are in **terminal characters** (columns and rows), not pixels. `(x=0, y=0)` is the top-left corner of the terminal.

When a widget is inside a `Box`, its `x` and `y` are **relative to the box's interior** (inside the border). The widget's absolute position is computed automatically.

### Widget lifecycle

1. You create widgets and set their properties.
2. You add them to a `Box` (or directly to `App`).
3. `App.run()` starts the event loop, which repeatedly calls `render()` → each widget's `draw()` → input handling.

---

## Widgets

### `App`

The root of every cozy_tui application. Manages the render loop, focus, scrolling, and global key handlers.

```python
App(full=True, size="800x600", style=Style(...))
```

| Parameter | Description |
|-----------|-------------|
| `full` | `True` to use the full terminal size (recommended). `False` uses `size`. |
| `size` | `"WxH"` string in virtual units when `full=False`. Each unit = 30 characters. |
| `style` | Background style for the entire screen. |

**Methods:**

```python
app.add(widget)             # Add a top-level widget
app.focus(widget)           # Set the initially focused widget
app.on_key(key, func)       # Register a global key handler
                            # Return "quit" from func to exit the app
app.quit()                  # Exit the app from anywhere (e.g. inside a callback)
app.run()                   # Start the event loop (blocking)
```

**Example:**

```python
app = App(full=True, size=None, style=Style(fg="white", bg="black"))
app.on_key(Key.ESC, lambda: "quit")
app.on_key(Key.CTRL_C, lambda: "quit")
app.run()
```

---

### `Box`

A bordered container that holds other widgets. The border is highlighted when any child has focus.

```python
Box(x, y, size, text="", border="single", style=None, title="")
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position in terminal characters |
| `size` | `"WxH"` string in virtual pixels — divide by `30` to get character dimensions. `"900x600"` = 30 cols × 20 rows. |
| `text` | Optional centered text in the box interior |
| `border` | Border style: `"single"`, `"double"`, `"rounded"`, `"bold"`, `"none"` |
| `style` | Style for the box background and border |
| `title` | Optional title shown in the top border |

**Methods:**

```python
box.add(widget)   # Add a child widget (positions are relative to box interior)
```

**Border styles:**

| Style | Appearance |
|-------|-----------|
| `"single"` | `+--+` / `\|` |
| `"double"` | `╔══╗` / `║` |
| `"rounded"` | `╭──╮` / `│` |
| `"bold"` | `┏━━┓` / `┃` |
| `"none"` | No border |

**Example:**

```python
box = Box(1, 1, "60x20", border="rounded", style=Style(fg="white", bg="black"), title="My App")
box.add(Label(2, 2, "Hello!"))
app.add(box)
```

---

### `Label`

A non-interactive static text widget.

```python
Label(x, y, text, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `text` | The text to display |
| `style` | Optional style override |

You can update the label's text at any time by setting `.text`:

```python
lbl = Label(2, 5, "Status: idle")
# later...
lbl.text = "Status: done"
```

---

### `Input`

A focusable text input field. Supports single-line and multi-line modes.

```python
Input(x, y, width, placeholder="", style=None, cursor=True, cursor_style="vertical",
      flash=True, multiline=False, masked=False, masked_symbol="*")
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `width` | Display width in characters |
| `placeholder` | Ghost text shown when the field is empty |
| `style` | Style when unfocused (defaults to terminal reset) |
| `cursor` | Whether to show the cursor (`True` by default) |
| `cursor_style` | `"vertical"` (default), `"block"`, or `"underline"` |
| `flash` | Whether the cursor blinks (`True` by default) |
| `multiline` | Enables multi-line editing — Enter or Shift+Enter inserts a newline |
| `masked` | Hide typed characters (e.g. for passwords). `False` by default. |
| `masked_symbol` | Character used for masking. Defaults to `"*"`. |

**Reading the value:**

```python
value = inp.value    # direct attribute
value = inp.get()    # method
```

**Cursor styles:**

| Style | Description |
|-------|-------------|
| `"vertical"` | The terminal's real blinking cursor bar (smooth, OS-rendered) |
| `"block"` | Inverted color block drawn over the character at the cursor |
| `"underline"` | Underlined character at the cursor |

**Multi-line mode:**

When `multiline=True`, the input stores newlines in `.value`. Press Enter or Shift+Enter to insert a newline; use UP/DOWN arrows to move between lines.

**Masked mode:**

When `masked=True`, typed characters are replaced visually by `masked_symbol` (default `"*"`). The real text is still stored in `.value` and used for validation — only the display is affected.

**Example:**

```python
name_input = Input(10, 2, 25, placeholder="Your name")
pass_input = Input(10, 4, 25, placeholder="Password", masked=True)
notes_input = Input(10, 6, 25, placeholder="Notes...", multiline=True)
box.add(name_input)
box.add(pass_input)
box.add(notes_input)
```

---

### `Button`

A focusable button that executes a callback when activated. Activates on Enter, Space, or mouse click.

```python
Button(x, y, text, width=None, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `text` | Label shown on the button |
| `width` | Total width in characters. Defaults to `len(text) + 4` (minimum 8). Set larger to add breathing room. |
| `style` | `fg` = text color, `bg` = button background color |

**Methods:**

```python
btn.on_click(func)   # Register a callback (receives the button as argument); returns self for chaining
```

**Visual states:**

| State | Appearance |
|-------|-----------|
| Normal | Text centered on `bg` colored background |
| Focused | Colors inverted (`fg` becomes background, `bg` becomes text), bold |
| Pressed | Same as normal but dimmed, lasts ~0.3 seconds |

**Example:**

```python
btn = Button(2, 6, "Submit", size=20, style=Style(fg="white", bg="blue"))
btn.on_click(lambda: print("Submitted!"))
box.add(btn)
app.focus(btn)
```

**Chaining:**

```python
box.add(
    Button(2, 6, "Delete", width=16, style=Style(fg="white", bg="red"))
    .on_click(handle_delete)
)
```

---

### `Checkbox`

A focusable toggle widget. Clicking or pressing Enter/Space flips between checked and unchecked.

```python
Checkbox(x, y, text, checked=False, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `text` | Label shown next to the checkbox |
| `checked` | Initial checked state (`False` by default) |
| `style` | `fg` = text color, `bg` = background color |

**Reading the value:**

```python
cb.checked    # bool — True if checked
```

**Methods:**

```python
cb.on_change(func)   # Called with the new bool value whenever the checkbox is toggled
cb.on_click(func)    # Called with the widget itself on every toggle (same as Button)
```

Both methods return `self` for chaining.

**Visual states:**

| State | Appearance |
|-------|-----------|
| Unchecked | `[ ] Label text` — normal style |
| Checked | `[x] Label text` — bold |
| Focused | `[x] Label text` — black on white, bold |

**Example:**

```python
cb = Checkbox(2, 3, "Enable notifications", checked=True)
cb.on_change(lambda checked: print(f"Notifications: {checked}"))
box.add(cb)
```

**Chaining:**

```python
box.add(
    Checkbox(2, 5, "I agree to the terms")
    .on_change(lambda v: btn.on_click(submit if v else None))
)
```

---

### `MarkdownInput`

A multi-line text editor that renders its content as **live Markdown** using [Rich](https://github.com/Textualize/rich) when not focused. All editing behaviour is inherited from `Input` — only the rendering differs.

> **Requires Rich:** `pip install rich`  
> Falls back to plain `Input` rendering if Rich is not installed.

```python
MarkdownInput(x, y, width, placeholder="", style=None, multiline=True, ...)
```

All `Input` parameters are accepted. Typical usage sets `multiline=True` so the user can write multi-line Markdown.

**Behaviour:**

| State | Display |
|-------|---------|
| **Focused** | Raw Markdown source with blinking cursor — edit normally |
| **Unfocused** | Rich-rendered Markdown preview (headings, bold, italic, code, etc.) |

Tab cycles focus away; the preview appears instantly when another widget receives focus.

**Rendering pipeline:**

```
self.value  →  Rich Markdown renderer  →  ANSI output  →  canvas.write()
```

Rich renders with `color_system="standard"` (16 colours), so the preview respects the terminal palette. Truecolor values Rich uses internally are downsampled to the nearest standard colour.

**Caching:** The rendered output is cached by `(value, width)` — Rich only re-renders when the text or display width actually changes, not on every frame.

**Example:**

```python
from cozy_tui import App, Box, Button, MarkdownInput, Style
from cozy_tui.events import Key

app = App(full=True, size=None, style=Style(fg="white", bg="black"))

box = Box(2, 1, "2100x660", border="rounded",
          style=Style(fg="cyan", bg="black"), title=" Markdown Editor ")

editor = MarkdownInput(
    2, 2, 66,
    multiline=True,
    placeholder="# Title\n\nStart writing **Markdown** here...",
    style=Style(fg="white"),
)

preview_btn = Button(2, 20, "Preview (Tab)", width=18,
                     style=Style(fg="white", bg="bright_black"))
preview_btn.on_click(lambda b: app.focus(editor))

box.add(editor)
box.add(preview_btn)
app.add(box)
app.focus(editor)
app.on_key(Key.ESC, lambda: "quit")
app.run()
```

**Supported Markdown elements** (via Rich):

- Headings (`#`, `##`, `###`, ...)
- **Bold** (`**text**`), *italic* (`*text*`), `inline code` (`` `code` ``)
- Fenced code blocks (` ``` `)
- Blockquotes (`> text`)
- Horizontal rules (`---`)
- Unordered and ordered lists

**Extending:**

`MarkdownInput` is designed to be the first of a family of specialised editors that share `Input`'s editing engine:

```
Input
 ├── MarkdownInput   ← live Rich Markdown preview
 ├── CodeInput       ← syntax highlighting (future)
 └── RichTextInput   ← arbitrary Rich renderables (future)
```

To create your own, subclass `Input` and override `draw()` (and optionally `natural_height()`). Only the rendering path needs to change.

---

### `ListView` / `ListItem`

A scrollable, keyboard-navigable list of items. Items can be plain strings or `ListItem(text, value)` objects to separate display text from the returned value.

```python
ListView(x, y, items=None, *, width=None, height=None, style=None)
ListItem(text, value=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `items` | Initial list of strings or `ListItem` objects |
| `width` | Fixed width in chars. `None` = auto-sized from the widest item. |
| `height` | Number of visible rows. `None` = show all items. |

**Reading the value:**

```python
lv.selected        # value of the highlighted item
lv.selected_index  # integer index
```

**Mutating the list:**

```python
lv.append(item)          # add to the end
lv.insert(index, item)   # insert at position
lv.remove(item)          # remove by reference
lv.clear()               # remove all items
lv.set(value)            # jump to the item whose value equals value
```

**Callbacks:**

```python
lv.on_change(func)   # called with selected value when cursor moves (returns self)
lv.on_select(func)   # called with selected value when Enter is pressed or item clicked (returns self)
```

**Key bindings:** Up/Down — move, Home/End — first/last, Enter — confirm selection.

**Example:**

```python
from cozy_tui import ListView, ListItem

lv = ListView(2, 2, [
    ListItem("Python",     "py"),
    ListItem("JavaScript", "js"),
    ListItem("Rust",       "rs"),
], height=5)
lv.on_select(lambda val: print(f"Chose: {val}"))
box.add(lv)
```

---

### `Dropdown`

A collapsed header that opens a `ListView` popup when activated. Only one row tall when closed; expands downward when open.

```python
Dropdown(x, y, items=None, *, width=None, height=6, style=None, placeholder=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `items` | Initial list of strings or `ListItem` objects |
| `width` | Fixed header width. `None` = auto from items. |
| `height` | Max visible rows in the popup (default `6`) |
| `placeholder` | Ghost text shown when no item is selected |

**Reading the value:**

```python
dd.selected        # value of the confirmed selection
dd.selected_index  # integer index
```

**Mutating the list:** same API as `ListView` — `append`, `insert`, `remove`, `clear`, `set`.

**Callbacks:**

```python
dd.on_change(func)   # called with value when confirmed (returns self)
dd.on_select(func)   # alias — called on same event (returns self)
```

**Key bindings:** Enter/Space/Down — open; Up/Down — navigate; Enter — confirm; Esc/Space — close without confirming.

**Example:**

```python
from cozy_tui import Dropdown, ListItem, Style

dd = Dropdown(2, 2, [
    ListItem("Option A", "a"),
    ListItem("Option B", "b"),
    ListItem("Option C", "c"),
], placeholder="Select one...", style=Style(fg="white"))
dd.on_change(lambda val: print(f"Selected: {val}"))
box.add(dd)
```

---

### `ProgressBar`

A non-interactive horizontal progress bar. Displays `[====    ] NNN%`.

```python
ProgressBar(x, y, fill="=", empty=" ", progress=0, *, width=20, min=0, max=100, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `fill` | Character for the filled portion (default `"="`) |
| `empty` | Character for the empty portion (default `" "`) |
| `progress` | Initial value (default `0`) |
| `width` | Total width in characters including the `[ ] NNN%` frame (default `20`) |
| `min` | Minimum value (default `0`) |
| `max` | Maximum value (default `100`) |

**Methods:**

```python
bar.set(value)           # set the value directly (clamped to min–max)
bar.increment(amount=1)  # add amount to current value
bar.decrement(amount=1)  # subtract amount from current value
bar.get()                # return current value
bar.on_change(func)      # called with new value whenever it changes
```

**Example:**

```python
from cozy_tui import ProgressBar, Style

bar = ProgressBar(2, 5, fill="█", empty="░", width=30,
                  style=Style(fg="bright_green"))
bar.set(42)
box.add(bar)
```

---

## Layouts

Layouts are borderless containers that **automatically position their children** — you don't set `x`/`y` on children added to a layout. They inherit from `Widget` and can be placed anywhere a widget can (inside a `Box`, directly on `App`, or nested inside other layouts).

All layouts support `.add(widget)` which returns `self` for chaining.

### `Layout` (base)

The base class for all layouts. Not used directly — subclass it and implement `_arrange()` to set each child's `x`, `y`, and update `self._computed_width` / `self._computed_height`.

```python
class MyLayout(Layout):
    def _arrange(self):
        # position self.children, then set:
        self._computed_width = ...
        self._computed_height = ...
```

---

### `VBox`

Stack children **vertically**, top to bottom. Width grows to the widest child; height is the sum of child heights plus gaps.

```python
VBox(x, y, gap=0, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `gap` | Blank rows between children (default `0`) |

**Example:**

```python
from cozy_tui import VBox, Label, Button, Style

vbox = VBox(2, 2, gap=1)
vbox.add(Label(0, 0, "Name:"))
vbox.add(Input(0, 0, 20, placeholder="Enter name"))
vbox.add(Button(0, 0, "Submit", width=20, style=Style(fg="white", bg="blue")))
box.add(vbox)
```

> Children's `x`/`y` are ignored — the layout computes them. Pass `0, 0` or any placeholder.

---

### `HBox`

Stack children **horizontally**, left to right. Height grows to the tallest child; width is the sum of child widths plus gaps.

```python
HBox(x, y, gap=0, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `gap` | Blank columns between children (default `0`) |

**Example:**

```python
from cozy_tui import HBox, Button, Style

hbox = HBox(2, 10, gap=2)
hbox.add(Button(0, 0, "OK", width=10, style=Style(fg="white", bg="green")))
hbox.add(Button(0, 0, "Cancel", width=10, style=Style(fg="white", bg="red")))
box.add(hbox)
```

---

### `Grid`

Arrange children in a **fixed number of columns**, filling left to right, top to bottom. Column widths are sized to the widest child in each column; row heights to the tallest child in each row.

```python
Grid(x, y, cols, gap_x=1, gap_y=0, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `cols` | Number of columns |
| `gap_x` | Horizontal gap between columns (default `1`) |
| `gap_y` | Vertical gap between rows (default `0`) |

**Example:**

```python
from cozy_tui import Grid, Checkbox

grid = Grid(2, 2, cols=2, gap_x=4, gap_y=1)
for option in ["Red", "Green", "Blue", "Yellow"]:
    grid.add(Checkbox(0, 0, option))
box.add(grid)
```

This renders as:

```
[✔] Red      [✔] Green
[✔] Blue     [✔] Yellow
```

---

## Styling

Styles are created with the `Style` class:

```python
Style(fg="color", bg="color", styles=["bold", "dim", "underline"])
```

**Available colors:**

`black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`,
`bright_black`, `bright_red`, `bright_green`, `bright_yellow`,
`bright_blue`, `bright_magenta`, `bright_cyan`, `bright_white`

**Text styles:** `"bold"`, `"dim"`, `"underline"`

**Example:**

```python
Style(fg="white", bg="blue")                      # white text on blue background
Style(fg="bright_white", bg="black", styles=["bold"])   # bold bright white on black
Style(fg="cyan")                                  # cyan text, default background
```

---

## Key Bindings

### Global (handled by App)

| Key | Action |
|-----|--------|
| Tab | Focus next widget |
| Shift+Tab | Focus previous widget |
| Ctrl+C | Exit the app |
| Scroll Up / Page Up / Ctrl+Up | Scroll content up |
| Scroll Down / Page Down / Ctrl+Down | Scroll content down |

### Input widget

| Key | Action |
|-----|--------|
| Arrow keys | Move cursor |
| Home / End | Jump to line start / end |
| Backspace | Delete character behind cursor |
| Delete | Delete character ahead of cursor |
| Enter / Shift+Enter | Insert newline (multiline mode only) |
| UP / DOWN | Move between lines (multiline mode only) |

### Button widget

| Key | Action |
|-----|--------|
| Enter | Activate button |
| Space | Activate button |

### Checkbox widget

| Key | Action |
|-----|--------|
| Enter | Toggle checked state |
| Space | Toggle checked state |

### Registering custom global shortcuts

```python
app.on_key(Key.ESC, lambda: "quit")      # return "quit" to exit
app.on_key(Key.ENTER, submit_form)        # any function works too
```

Available key constants in `cozy_tui.events.Key`:

`ESC`, `ENTER`, `BACKSPACE`, `TAB`, `SHIFT_TAB`, `SHIFT_ENTER`,
`UP`, `DOWN`, `LEFT`, `RIGHT`, `HOME`, `END`,
`DELETE`, `PAGE_UP`, `PAGE_DOWN`,
`CTRL_UP`, `CTRL_DOWN`, `CTRL_C`

---

## Mouse Support

Mouse clicks are handled automatically:

- **Click any focusable widget** → gives it focus
- **Click a Button** → gives it focus and activates it
- **Click a Checkbox** → gives it focus and toggles it
- **Scroll wheel** → scrolls the app content up/down

No extra setup needed — mouse support is enabled automatically when `app.run()` starts.

---

## Focus System

Focus determines which widget receives keyboard input. Only `focusable` widgets (`Input`, `Button`, `Checkbox`, `ListView`, `Dropdown`) can hold focus.

```python
app.focus(widget)      # set initial focus manually
```

While running:
- **Tab** moves focus to the next focusable widget
- **Shift+Tab** moves focus to the previous one
- **Mouse click** focuses the clicked widget

Focused widgets receive a visual highlight — inputs show a white background and a blinking cursor; buttons invert their colors and go bold. The parent `Box` also highlights its border when any child has focus.

---

## Scrolling

When content is taller than the terminal, the app scrolls vertically. Scroll controls:

| Key / Action | Effect |
|---|---|
| Scroll wheel up | Scroll up 3 rows |
| Scroll wheel down | Scroll down 3 rows |
| Page Up / Ctrl+Up | Scroll up 3 rows |
| Page Down / Ctrl+Down | Scroll down 3 rows |

---

## Examples

The `examples/` directory contains runnable apps. Each example adds the project root to `sys.path` automatically, so they can be run from any directory.

### `examples/basic/basic.py` — Hello World

Minimal app with a label and a quit button. Good starting point.

```bash
python examples/basic/basic.py
```

### `examples/timer_app/timer.py` — Timer / Forms

Demonstrates `Input`, `Button`, `Checkbox`, `ProgressBar`, `Dropdown`, `ListView`, `VBox`, `HBox`, and `Grid` in a single app.

```bash
python examples/timer_app/timer.py
```

### `examples/calculator_app/calculator.py` — Calculator

A fully keyboard-driven calculator supporting `+`, `-`, `×`, `÷`, `**` (exponent), `√` (square root), and `!` (factorial).

```bash
python examples/calculator_app/calculator.py
```

**Calculator keyboard shortcuts:**

| Key | Action |
|---|---|
| `0`–`9`, `.` | Enter digits |
| `+` `-` `*` `/` | Arithmetic operators (`*` inserts `×`, `/` inserts `÷`) |
| `^` | Exponent (`**`) |
| `r` | Square root (`√(`) |
| `!` | Factorial |
| Enter / `=` | Evaluate |
| Backspace | Delete last character |
| `c` | Clear |
| ESC | Quit |
