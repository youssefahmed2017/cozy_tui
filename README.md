# cozy_tui

[![CI](https://github.com/youssefahmed2017/cozy_tui/actions/workflows/ci.yml/badge.svg)](https://github.com/youssefahmed2017/cozy_tui/actions/workflows/ci.yml)

A lightweight, cross-platform Python TUI (Terminal User Interface) library. Build keyboard-driven terminal apps with widgets, focus management, mouse support, and smooth cursor blinking — all rendered through raw VT sequences. Runs on Windows (Console API) and POSIX (Linux/macOS via `termios`).

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
  - [AnimatedLabel / GlowAnimation](#animatedlabel--glowanimation)
  - [Text](#text)
  - [Input](#input)
  - [Button](#button)
  - [Checkbox](#checkbox)
  - [MarkdownInput](#markdowninput)
  - [ListView / ListItem](#listview--listitem)
  - [CheckList / CheckItem](#checklist--checkitem)
  - [Dropdown](#dropdown)
  - [ProgressBar](#progressbar)
  - [Table / TableRow](#table--tablerow)
  - [Collapsible](#collapsible)
  - [Tree / TreeNode](#tree--treenode)
- [Layouts](#layouts)
  - [Layout (base)](#layout-base)
  - [VBox](#vbox)
  - [HBox](#hbox)
  - [Grid](#grid)
- [Dock Layout](#dock-layout)
- [Overlays & Modals](#overlays--modals)
- [Styling](#styling)
- [Key Bindings](#key-bindings)
- [Mouse Support](#mouse-support)
- [Focus System](#focus-system)
- [Scrolling](#scrolling)
- [Examples](#examples)

---

## Features

- **Cross-platform** — runs on Windows (Console API) and POSIX (Linux/macOS via `termios`); the backend is chosen automatically.
- **Very few dependencies** — almost pure Python. The clipboard is built in (no `pyperclip`); `rich` is the only third-party package, used for `Markdown`/`MarkdownInput` and imported defensively. Everything else is the standard library.
- **Built-in clipboard** — `cozy_tui.clipboard.copy`/`paste` with native backends per platform (Win32 API, `pbcopy`/`pbpaste`, `wl-clipboard`/`xclip`/`xsel`, or OSC 52 fallback).
- **Unicode-aware rendering** — a built-in `wcwidth`-style width layer keeps CJK/emoji (double-width) and combining marks (zero-width) aligned in the cell grid.
- **Widgets**: `Button`, `Checkbox`, `Input`, `Label`, `AnimatedLabel`, `Text`, `Box`, `MarkdownInput`, `ListView`, `CheckList`, `Dropdown`, `ProgressBar`, `Table`, `Collapsible`, `Tree`
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

## Requirements

- Python 3.10+
- A VT-capable terminal on **Windows** (Windows Console API) or **POSIX** (Linux/macOS, via `termios`/`tty`). The console backend is selected automatically at import.

---

## Installation

Install from a checkout with pip (editable is handy for development):

```bash
git clone https://github.com/youssefahmed2017/cozy_tui.git
cd cozy_tui
pip install -e .            # add [dev] for the test suite; pip install rich for MarkdownInput
```

Or just clone and import directly — each example adds the project root to `sys.path`, so no install is strictly required.

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
app.dock(widget, side)      # Dock a widget to "left"/"right"/"top"/"bottom"/"fill"
                            # (see the Dock Layout section)
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

A bordered container that holds other widgets. Tab **dives into the box's first focusable child** rather than stopping on the box, so a box wrapping a form focuses the first field directly. Its border highlights whenever the box or any child has focus. A box is **not** itself a Tab stop by default — pass `focusable=True` to make an empty or decorative box selectable/clickable in its own right (diving into children still takes precedence when the box has focusable content).

```python
Box(x, y, size, text="", border="single", style=None, title="", focusable=False)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position in terminal characters |
| `size` | `"WxH"` string in virtual pixels — divide by `30` to get character dimensions. `"900x600"` = 30 cols × 20 rows. |
| `text` | Optional centered text in the box interior |
| `border` | Border style: `"single"`, `"double"`, `"rounded"`, `"bold"`, `"none"` |
| `style` | Style for the box background and border |
| `title` | Optional title shown in the top border |
| `focusable` | Make the box itself a Tab stop / clickable (`False` by default). Tab dives into focusable children regardless of this flag. |

**Methods:**

```python
box.add(widget)              # Add a child widget (positions relative to box interior)
box.dock(widget, side)       # Dock a child to an interior edge or "fill"
                             # (see the Dock Layout section)
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

### `AnimatedLabel` / `GlowAnimation`

A label whose text is rendered with a per-character animated color wave. Useful for decorative headers or status lines.

```python
AnimatedLabel(x, y, text, animation, *, style=None)
GlowAnimation(colors=None, interval=0.05)
```

| Parameter | Description |
|-----------|-------------|
| `text` | The text to animate |
| `animation` | A `GlowAnimation` instance (or any object with `.colors` and `.interval`) |
| `colors` | List of named or hex colors cycling across the text characters |
| `interval` | Seconds between animation frames (default `0.05`) |

**Example:**

```python
from cozy_tui import AnimatedLabel, GlowAnimation

anim = GlowAnimation(
    colors=["red", "yellow", "green", "cyan", "blue", "magenta"],
    interval=0.08,
)
lbl = AnimatedLabel(2, 2, "cozy_tui", anim)
app.add(lbl)
```

The wave shifts one character position each frame, producing a smooth color sweep across the text.

---

### `Text`

A read-only multi-line text display with automatic word wrapping and optional scrolling. Useful for help text, logs, or any longer content.

```python
Text(x, y, *, width, height, text="", align="left", show_border=False, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `width` | Display width in characters (inner text area) |
| `height` | Number of visible rows (inner text area) |
| `text` | Initial text content. Use `\n` for explicit line breaks. |
| `align` | `"left"` (default), `"center"`, or `"right"` |
| `show_border` | Draw a single-line border around the widget (`False` by default). The border turns bold-white when focused. |

**Updating the text:**

```python
txt.text = "New content goes here."
txt.set("Also works via set().")
```

**Key bindings (when focused):**

| Key | Action |
|-----|--------|
| Up / Scroll Up | Scroll up one line |
| Down / Scroll Down | Scroll down one line |
| Page Up | Scroll up by height |
| Page Down | Scroll down by height |
| Home | Jump to the first line |
| End | Jump to the last line |

**Example:**

```python
from cozy_tui import Text, Style

txt = Text(2, 2, width=50, height=10, align="left", show_border=True,
           text="Lorem ipsum dolor sit amet, consectetur adipiscing elit.")
app.add(txt)
app.focus(txt)
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

---

### `MarkdownInput`

A multi-line text editor that renders its content as **live Markdown** using [Rich](https://github.com/Textualize/rich) when not focused. All editing behaviour is inherited from `Input` — only the rendering differs.

> **Requires Rich:** `pip install rich`  
> Falls back to plain `Input` rendering if Rich is not installed. Warnings are
> **off by default** (`COZY_TUI_NO_WARNINGS` defaults to `1`). Opt in by setting
> `COZY_TUI_NO_WARNINGS=0` (any of `0`/`false`/`no`/`off`); then, if Rich is
> missing, `App.run()` prints a one-time warning to stderr **after it exits and
> the screen is restored**:
> `WARNING    Rich isn't installed so you won't get Markdown/MarkdownInput as real markdown.`

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

**Example:**

```python
from cozy_tui import App, Box, Button, MarkdownInput, Style

editor = MarkdownInput(2, 2, 66, multiline=True,
                       placeholder="# Title\n\nStart writing **Markdown** here...")
box.add(editor)
app.focus(editor)
```

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

### `CheckList` / `CheckItem`

A scrollable list where each item has an independent checked state. Combines `ListView`-style navigation with `Checkbox`-style toggling — every row shows `[ ]` or `[✔]` and can be toggled individually.

```python
CheckList(x, y, items=None, *, width=None, height=None, style=None)
CheckItem(text, value=None, checked=False)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `items` | Initial list of strings or `CheckItem` objects |
| `width` | Fixed width in chars. `None` = auto-sized from the widest item. |
| `height` | Number of visible rows. `None` = show all items. |

**Reading values:**

```python
cl.selected        # value of the highlighted item
cl.selected_index  # integer index of the highlighted item
cl.checked_values  # list of .value for every checked item
cl.checked_items   # list of CheckItem objects for every checked item
```

**Mutating the list:**

```python
cl.append(item)                # add to the end (string or CheckItem)
cl.insert(index, item)         # insert at position
cl.remove(item)                # remove by reference
cl.clear()                     # remove all items
cl.set_checked(value, checked) # flip one item's state by value
```

**Bulk operations** (do not fire `on_toggle`):

```python
cl.check_all()    # check every item
cl.uncheck_all()  # uncheck every item
cl.toggle_all()   # flip every item's state
```

**Callbacks:**

```python
cl.on_change(func)   # func(value) — called when the cursor moves to a different row (returns self)
cl.on_toggle(func)   # func(value, checked) — called when an item is toggled by the user (returns self)
```

**Key bindings:** Up/Down — move cursor, Home/End — first/last, Enter/Space — toggle highlighted item.

**Mouse:** clicking a row moves the cursor to it and toggles it immediately.

**Example:**

```python
from cozy_tui import CheckList, CheckItem, Style

cl = CheckList(2, 2, [
    CheckItem("Buy groceries"),
    CheckItem("Walk the dog", checked=True),
    CheckItem("Finish report"),
], height=5, style=Style(fg="white"))

cl.on_toggle(lambda value, checked: print(f"{value}: {checked}"))
box.add(cl)
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

**Key bindings:** Enter/Space/Down — open; Up/Down — navigate; Enter or click a row — confirm; Esc or click outside — close without confirming.

The open popup is rendered on the [overlay layer](#overlays--modals), so it **floats above every other widget** (never clipped or overpainted) and the header stays a single row — opening it no longer pushes surrounding widgets down.

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

### `Table` / `TableRow`

A scrollable, keyboard-navigable table with sortable columns and optional border.

```python
Table(x, y, *, height=None, show_header=True, show_border=False, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `height` | Number of visible data rows. `None` = show all rows. |
| `show_header` | Draw the column header row (default `True`) |
| `show_border` | Draw a border around the table (default `False`) |

**Building the table:**

```python
tbl.add_column(title, *, width=None, align="left")
tbl.add_row(*values, style=None, disabled=False, metadata=None)
tbl.insert_row(index, *values, ...)
tbl.remove_row(index)
tbl.set_cell(row_index, col_index, value)
tbl.update_row(index, *values)
tbl.sort(column, *, reverse=False)   # column = title string or int index
tbl.clear()
```

**`TableRow`** — the object returned by iteration and `selected_row`:

```python
row = tbl.selected_row     # TableRow | None
row[0]                     # access column value by index
list(row)                  # iterate all values
row.style                  # per-row style override
row.disabled               # skip focus/highlight if True
row.metadata               # arbitrary user data attached to this row
```

**Callbacks:**

```python
tbl.on_change(func)   # func(row) — called when selection moves
tbl.on_select(func)   # func(row) — called on Enter or click
```

**Key bindings:**

| Key | Action |
|-----|--------|
| Up / Down | Move row selection |
| Left / Right | Move column highlight |
| Home / End | First / last row |
| Enter | Fire `on_select` |

**Example:**

```python
from cozy_tui import Table, Style

tbl = Table(2, 2, height=8, show_border=True)
tbl.add_column("Name",  width=16)
tbl.add_column("Lang",  width=12)
tbl.add_column("Stars", width=8, align="right")

tbl.add_row("cozy_tui",  "Python", "★★★★")
tbl.add_row("rich",      "Python", "★★★★★")
tbl.add_row("textual",   "Python", "★★★★★")

tbl.sort("Stars", reverse=True)
tbl.on_select(lambda row: print(row[0]))
app.add(tbl)
```

---

### `Collapsible`

A focusable expand/collapse container. Children are navigated with Up/Down while the `Collapsible` holds focus — Tab does not descend into individual children.

```python
Collapsible(x, y, *, title="", expanded=True, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `title` | Text shown in the header row |
| `expanded` | Whether to start open (`True` by default) |

**Adding children:**

```python
coll.add(widget)              # any Widget — Button, Checkbox, Label, …
coll.add(ListItem("text", v)) # or a ListItem for text-only rows
coll.add("plain string")      # plain strings work too
```

All items (widgets and text) are laid out sequentially, one row each. Widget children draw in their active/focused style when the cursor is on them. Text items render with a `> ` selection prefix.

**Expand/collapse API:**

```python
coll.expand()
coll.collapse()
coll.toggle()
coll.on_toggle(func)   # func(expanded: bool)
```

**Key bindings (when focused):**

| Key | Action |
|-----|--------|
| Up / Down | Move cursor through children |
| Left | Collapse |
| Right | Expand |
| Enter / Space | Activate selected child (or expand if collapsed) |
| Home / End | First / last child |

**Callbacks:**

```python
coll.on_select(func)   # func(value) — fires when Enter is pressed on a text item
coll.on_toggle(func)   # func(expanded) — fires when the section expands or collapses
```

**Example:**

```python
from cozy_tui import Collapsible, Checkbox, ListItem

section = Collapsible(2, 2, title="Theme", expanded=True)
section.add(ListItem("Dark",      "dark"))
section.add(ListItem("Light",     "light"))
section.add(ListItem("Solarized", "solarized"))
section.on_select(lambda val: print(f"Theme: {val}"))
app.add(section)
```

---

### `Tree` / `TreeNode`

A hierarchical tree view where each node can be expanded or collapsed. Navigation moves through the flat list of currently visible nodes.

```python
Tree(x, y, *, height=None, connectors=False, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `height` | Number of visible rows. `None` = show all visible nodes. |
| `connectors` | Draw `├──`, `└──`, `│` branch lines (default `False`) |

**Building the tree:**

```python
root  = tree.add("Project")        # returns a TreeNode
child = root.add("src")            # TreeNode — chains naturally
child.add("main.py")
child.add("app.py")
```

Every `add()` call returns a `TreeNode`, so nesting is expressed by method chaining.

**`TreeNode` API:**

```python
node.add(text)       # append a child, return it
node.expand()        # set expanded = True
node.collapse()      # set expanded = False
node.toggle()        # flip expanded (no-op on leaf)
node.is_leaf         # True if no children
node.text            # display text
node.expanded        # current expand state
node.metadata        # arbitrary user data slot
```

**Key bindings (when focused):**

| Key | Action |
|-----|--------|
| Up / Down | Move selection through visible nodes |
| Right | Expand the selected node |
| Left | Collapse (if expanded) or jump to parent (if collapsed) |
| Enter / Space | Toggle expand/collapse; fires `on_select` |
| Home / End | First / last visible node |

**Callbacks:**

```python
tree.on_select(func)   # func(node) — fires on Enter or click
tree.on_change(func)   # func(node) — fires when selection moves
```

**Example (without connectors):**

```python
from cozy_tui import App, Tree

app = App()
tree = Tree(2, 2)

project = tree.add("Project")
project.expand()

src = project.add("src")
src.expand()
src.add("main.py")
src.add("app.py")

widgets = src.add("widgets")
widgets.add("button.py")
widgets.add("checkbox.py")

project.add("docs").add("README.md")

tree.on_select(lambda node: print(node.text))
app.add(tree)
app.focus(tree)
app.run()
```

**Connector rendering** (`connectors=True`):

```
v Project
├── v src
│   ├── main.py
│   ├── app.py
│   └── > widgets
└── > docs
```

After expanding `widgets`:

```
v Project
├── v src
│   ├── main.py
│   ├── app.py
│   └── v widgets
│       ├── button.py
│       └── checkbox.py
└── > docs
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

## Dock Layout

Instead of positioning widgets by hand, you can **dock** them to the edges of a container. Both `App` and `Box` have a `dock()` method:

```python
app.dock(widget, side, margin=0)   # dock to a screen edge
box.dock(widget, side, margin=0)   # dock to a box interior edge
```

`side` is one of `"left"`, `"right"`, `"top"`, `"bottom"`, or `"fill"`.

### How space is divided

Docking works by consuming a **shrinking rectangle**. The container starts with its full area; each dock carves a band off one edge, and the next dock only sees what's left:

- `top` / `bottom` → take a horizontal band; the widget **stretches across the remaining width**.
- `left` / `right` → take a vertical band; the widget **stretches across the remaining height**.
- `fill` → takes the **entire leftover rectangle** — this is who "gets the rest of the space."

**Order matters.** Docks are applied in the order you add them, so the widget docked last sees the smallest rectangle:

```python
app.dock(header,  "top")     # full width, along the top
app.dock(status,  "bottom")  # full width, along the bottom
app.dock(sidebar, "left")    # spans only the band BETWEEN header and status
app.dock(main,    "fill")    # everything that's left
```

```
+----------------------------------+
| Header                           |
+------+---------------------------+
| Side | Main (fill)               |
| Bar  |                           |
+------+---------------------------+
| Status                           |
+----------------------------------+
```

Had you docked the sidebar *before* the header and status, it would span the full terminal height instead.

### Stretching and `margin`

Whether a docked widget actually *fills* its band depends on the widget. A `Box` grows to fill the slice it's given (so a docked `Box` spans the full width/height of its band automatically); fixed-size widgets like `Label` simply anchor at the slice's top-left corner. `margin` insets the widget from the edge it docks against.

### Reactive by design

Docks are recomputed **every frame**, so the layout re-flows automatically when the terminal is resized — no manual repositioning needed. Docking returns the widget, so calls can be chained or captured:

```python
sidebar = app.dock(Box(0, 0, "180x10", title="Menu"), "left", margin=1)
```

> On non-`full` (scrollable) apps, docked widgets scroll with the content rather than staying pinned to the viewport. For the typical `full=True` app there is no scroll, so they stay anchored.

See [`examples/dock_layout/dock_layout.py`](examples/dock_layout/dock_layout.py) for a complete header / sidebar / status / fill layout.

---

## Overlays & Modals

Overlays draw a widget **above** the rest of the UI on a separate z-layer — the basis for dialogs, menus, and tooltips. Push one with `app.open_overlay(widget)` and remove it with `app.close_overlay()`.

```python
def confirm(_btn):
    dialog = Box(0, 0, "520x180", title="Confirm", border="rounded")
    dialog.add(Label(2, 1, "Delete everything?"))
    dialog.add(Button(2, 4, "Cancel").on_click(lambda b: app.close_overlay(dialog)))
    dialog.add(Button(14, 4, "Delete").on_click(lambda b: app.close_overlay(dialog)))
    app.open_overlay(dialog, close_on_click_outside=True)
```

```python
app.open_overlay(widget, *, modal=True, dim=True, center=True,
                 close_on_escape=True, close_on_click_outside=False, on_close=None)
app.close_overlay(widget=None)   # topmost, or the overlay wrapping `widget`
```

| Option | Meaning |
|--------|---------|
| `modal` | Confine keyboard focus and mouse input to the overlay (Tab cycles only inside it). Non-modal overlays are purely visual, e.g. tooltips. |
| `dim` | Grey the background behind the overlay as a scrim. |
| `center` | Re-centre the widget on screen every frame (survives resize). Set `False` to position it yourself via `x`/`y`. |
| `close_on_escape` | Esc dismisses the topmost modal (default `True`). |
| `close_on_click_outside` | A click outside the overlay dismisses it (default `False`). |
| `on_close` | `func(widget)` called when the overlay closes. |

**Behaviour:**

- Overlays are **screen-fixed** — unaffected by scrolling — and stack (last opened is topmost).
- Opening a modal moves focus to its first focusable child; closing restores the focus that was active before.
- A `Box` is the natural overlay container (it gives the dialog a border, title, and hit-testing). Its border highlights while it holds focus.

See [`examples/overlay/overlay.py`](examples/overlay/overlay.py) for a dismissable confirm dialog.

### Text-entry prompt

For the common case of "ask the user for a line of text", `app.prompt()` wraps the `PromptDialog` widget and the overlay plumbing into one call:

```python
app.prompt("Rename card", initial=card.text,
           on_submit=lambda text: rename(card, text),   # Enter
           on_cancel=lambda: None)                       # Esc / click outside
```

```python
app.prompt(title, initial="", *, on_submit=None, on_cancel=None,
           width=40, close_on_click_outside=True)   # returns the PromptDialog
```

Enter fires `on_submit(text)` and closes the dialog; Esc or a click outside fires `on_cancel()`. It's a centered, dimmed modal, so focus and input are confined to it. The underlying `PromptDialog` is also exported if you want to compose it yourself.

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

Focus determines which widget receives keyboard input. Only `focusable` widgets (`Input`, `Button`, `Checkbox`, `ListView`, `Dropdown`, `Table`, `Collapsible`, `Tree`) can hold focus. A **focusable container defers to its children**: Tab dives into a `Box`'s first focusable child instead of stopping on the box. A `Box` is not a Tab stop on its own unless you construct it with `Box(..., focusable=True)`, which is useful for empty or decorative boxes you still want selectable.

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

### `examples/dock_layout/dock_layout.py` — Dock Layout

Demonstrates `App.dock()` with a header (`top`), status bar (`bottom`), sidebar (`left`), and a `fill` main area that claims the remaining space. Resize the terminal to watch the layout re-flow.

```bash
python examples/dock_layout/dock_layout.py
```

### `examples/overlay/overlay.py` — Overlays / Modals

A base screen with a button that opens a centered, dimmed modal dialog. Tab is confined to the dialog; Esc or a click outside dismisses it.

```bash
python examples/overlay/overlay.py
```

### `examples/command_palette/command_palette.py` — Command Palette

A Spotlight/VS Code-style fuzzy command launcher in a modal overlay: a custom widget with its own text buffer and filtered result list. Press `p` to open, type to fuzzy-search, Enter/click to run. Includes a background-worker command that keeps the UI responsive.

```bash
python examples/command_palette/command_palette.py
```

### `examples/kanban/kanban.py` — Kanban Board

A keyboard-driven To Do / Doing / Done board built from Boxes + ListViews. Tab switches columns, Up/Down selects, ←/→ moves a card between columns, `a`/`d` add/delete, `?` shows a help overlay, `c` opens a confirm-clear modal.

```bash
python examples/kanban/kanban.py
```

### `examples/snake/snake.py` — Snake

A real-time Snake game: a fully custom drawing widget painting the field cell-by-cell, driven by `app.tick_interval` (game logic decoupled from render rate), with a "Game Over" modal offering Restart / Quit.

```bash
python examples/snake/snake.py
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
