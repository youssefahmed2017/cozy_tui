# Widgets

### `App`

The root of every cozy_tui application. Manages the render loop, focus, scrolling, and global key handlers.

```python
App(full=True, size="800x600", style=Style(...))
```

| Parameter | Description                                                                   |
|-----------|-------------------------------------------------------------------------------|
| `full`    | `True` to use the full terminal size (recommended). `False` uses `size`.      |
| `size`    | `"WxH"` string in virtual pixels when `full=False`; divide by `App.SCALE` (10) for characters. `"800x600"` = 80 cols × 60 rows. |
| `style`   | Background style for the entire screen.                                       |
| `title`   | Terminal Tab Title (defaulted to Cozy TUI App)                                |

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
| `size` | `"WxH"` string in virtual pixels — divide by `App.SCALE` (10) to get the interior character dimensions. `"900x600"` = 90 cols × 60 rows. |
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

### `Hyperlink`

A focusable, clickable text link. When focused, **Enter** or **Space** opens the URL in the default web browser; a mouse **click** opens it directly. Renders like a `Label` (blue, bold, underlined) and highlights while focused.

```python
Hyperlink(x, y, text, link, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `text` | The visible link text |
| `link` | The URL to open (via the standard-library `webbrowser`) |
| `style` | Optional style override (defaults to blue + bold + underline) |

**Example:**

```python
from cozy_tui.widgets import Hyperlink

box.add(Hyperlink(2, 2, "cozy_tui on PyPI", "https://pypi.org/project/cozy-tui/"))
```

---

### `Bindings`

A self-sizing key-bindings legend — a bordered panel that lays out `key → description` rows with the keys aligned in a column. **You never give it a width or height**: it fits the widest key + description (and any section header or title).

```python
Bindings(x, y, bindings, *, title=None, border="rounded", style=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `bindings` | Either a flat `{key: description}` dict, or a grouped `{section: {key: description}}` dict |
| `title` | Optional title shown in the top border |
| `border` | Border style: `"single"`, `"double"`, `"rounded"` (default), `"bold"`, `"none"` |
| `style` | Optional style override (its `bg` tints the whole panel) |

**Flat:**

```python
app.add(Bindings(60, 2, {
    "↑": "Move Up",
    "↓": "Move Down",
    "Enter": "Select",
    "Esc": "Quit",
}, title="Keys"))
```

**Sectioned** (dict order is preserved):

```python
app.add(Bindings(60, 2, {
    "Movement": {"↑": "Move Up", "↓": "Move Down"},
    "Actions":  {"Enter": "Select", "Esc": "Quit"},
}))
```

renders as:

```
╭ Keys ─────────────╮      ╭───────────────────╮
│ ↑       Move Up   │      │ Movement          │
│ ↓       Move Down │      │ ↑       Move Up   │
│ Enter   Select    │      │ ↓       Move Down │
│ Esc     Quit      │      │                   │
╰───────────────────╯      │ Actions           │
                           │ Enter   Select    │
                           │ Esc     Quit      │
                           ╰───────────────────╯
```

The key column width is shared across all sections, so everything stays aligned. `Bindings` is non-interactive (display only).

---

### `AnimatedLabel` + animations

A label whose text is driven by an **animation** — a small object that turns the
text into a stream of positioned, colored glyphs each frame. The label
self-drives the frame loop (it calls `app.request_frame`), so you don't need to
set `app.tick_interval`.

```python
AnimatedLabel(x, y, text, *, animation, style=None)
```

Three built-in animations (all keyword-only args):

```python
GlowAnimation(*, colors=None, color_template=None, speed=0.06)
RainbowAnimation(*, spread=18, saturation=1.0, value=1.0, speed=0.06)
LevitateAnimation(*, mode="char", amplitude=4, phase=0.6, rate=0.15, speed=0.03)
```

**`GlowAnimation`** — a fixed palette cycled across the characters as a color wave.

| Parameter | Description |
|-----------|-------------|
| `colors` | List of hex colors (`"#ff8c00"`) or `(r, g, b)` tuples. Mutually exclusive with `color_template`. |
| `color_template` | A built-in gradient: `"orange"`, `"blue"`, `"green"`, `"red"`, `"purple"`. |
| `speed` | Seconds between frames (lower = faster). |

**`RainbowAnimation`** — sweeps the full HSV color wheel along the text and
rotates it over time (`6°`/frame).

| Parameter | Description |
|-----------|-------------|
| `spread` | Hue degrees between adjacent characters (wider = more colors on screen at once). |
| `saturation`, `value` | HSV saturation / brightness, `0.0`–`1.0`. |
| `speed` | Seconds between frames. |

**`LevitateAnimation`** — bobs the text up and down on a sine wave (motion, not
color; your own `style` is preserved).

| Parameter | Description |
|-----------|-------------|
| `mode` | `"word"` (whole text rises/falls together) or `"char"` (each character phase-shifted → a traveling wave). |
| `amplitude` | Peak rise in cells; text travels `0`–`2*amplitude` rows. The label sizes itself for this. |
| `phase` | Per-character phase shift in `"char"` mode. |
| `rate`, `speed` | Wave angular speed per frame / seconds between frames. |

> Color animations use **truecolor (RGB)**. Because `LevitateAnimation` occupies
> up to `2*amplitude` extra rows, `AnimatedLabel.natural_height` grows to match —
> leave room below it in a layout.

**Example:**

```python
from cozy_tui.widgets import AnimatedLabel, GlowAnimation, RainbowAnimation, LevitateAnimation

app.add(AnimatedLabel(2, 2, "cozy_tui", animation=GlowAnimation(color_template="blue")))
app.add(AnimatedLabel(2, 4, "rainbow!", animation=RainbowAnimation(spread=25)))
app.add(AnimatedLabel(2, 6, "floating", animation=LevitateAnimation(mode="char")))
```

Custom animations: subclass `Animation` and implement
`cells(text, style) -> iterable of (dx, dy, char, cell_style)`; set
`vertical_span` if your effect uses extra rows.

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
from cozy_tui import Style
from cozy_tui.widgets import Text

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
Button(x, y, text, style=None, width=None, *, animation=None, active_effect_duration=0.2)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `text` | Label shown on the button |
| `width` | Total width in characters. Defaults to `len(text) + 4` (minimum 8). Set larger to add breathing room. |
| `style` | `fg` = text color, `bg` = button background color |
| `animation` | **Keyword-only.** A color animation (`GlowAnimation`/`RainbowAnimation`) applied to the label text while the button is focused or hovered. |
| `active_effect_duration` | **Keyword-only.** Seconds the press "active" effect lasts (default `0.2`; `0` disables it). |

**Methods:**

```python
btn.on_click(func)   # Register a callback (receives the button as argument); returns self for chaining
btn.on_enter(func)   # Cursor entered the button (requires App(mouse_moves=True))
btn.on_leave(func)   # Cursor left the button
```

**Visual states** (least → most prominent):

| State | Appearance |
|-------|-----------|
| Normal | Text centered on `bg` colored background |
| Hovered | Bold (subtle lift); requires `App(mouse_moves=True)` |
| Focused | Colors inverted (`fg` becomes background, `bg` becomes text), bold |
| Active (pressed) | The whole button briefly **tints toward the screen background** (a "pressed-in" darkening), modelled on Textual's `-active` effect, for `active_effect_duration` seconds |

With `animation=`, the label text comes alive (animated color) while focused or
hovered — a Textual-style effect:

```python
from cozy_tui.widgets import Button, RainbowAnimation

btn = Button(2, 6, "Launch", animation=RainbowAnimation(speed=0.05))
```

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

> **Uses Rich.** `rich` is a required dependency of `cozy_tui` (installed automatically), so `Markdown`/`MarkdownInput` always render real Markdown.

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
from cozy_tui import App, Style
from cozy_tui.widgets import Box, Button, MarkdownInput

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

**Mouse:** clicking an item moves the cursor to it and confirms it. With `App(mouse_moves=True)`, hovering over an item highlights it (moves the cursor) without confirming — like arrow-key navigation.

**Example:**

```python
from cozy_tui.widgets import ListView, ListItem

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

**Mouse:** clicking a row moves the cursor to it and toggles it immediately. With `App(mouse_moves=True)`, hovering over a row highlights it (moves the cursor) without toggling.

**Example:**

```python
from cozy_tui import Style
from cozy_tui.widgets import CheckList, CheckItem

cl = CheckList(2, 2, [
    CheckItem("Buy groceries"),
    CheckItem("Walk the dog", checked=True),
    CheckItem("Finish report"),
], height=5, style=Style(fg="white"))

cl.on_toggle(lambda value, checked: print(f"{value}: {checked}"))
box.add(cl)
```

---

### `RadioSet` / `RadioItem`

A single-select list of options — exactly one is chosen at a time. Navigation mirrors `CheckList`, but selecting an option clears the previous one. The chosen option is marked `(•)`; the cursor is marked with `>`.

```python
RadioSet(x, y, items=None, *, selected=0, width=None, height=None, style=None)
RadioItem(text, value=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `items` | Initial list of strings or `RadioItem` objects |
| `selected` | Index of the initially selected option (default `0`) |
| `width` | Fixed width in chars. `None` = auto-sized from the widest item. |
| `height` | Number of visible rows. `None` = show all items. |

**Reading / setting the selection:**

```python
rs.selected        # value of the selected option
rs.selected_index  # integer index of the selected option
rs.selected_item   # the RadioItem object
rs.select(value)   # select the option whose .value == value
rs.select_index(i) # select by index
```

**Callbacks:**

```python
rs.on_change(func)   # func(value) — called when the selection changes (returns self)
```

**Key bindings:** Up/Down — move cursor, Home/End — first/last, Enter/Space — select the highlighted option.

**Mouse:** clicking a row moves the cursor to it and selects it immediately. With `App(mouse_moves=True)`, hovering over a row highlights it (moves the cursor) without selecting.

**Example:**

```python
from cozy_tui import Style
from cozy_tui.widgets import RadioSet, RadioItem

rs = RadioSet(2, 2, [
    RadioItem("Small", value="s"),
    RadioItem("Medium", value="m"),
    RadioItem("Large", value="l"),
], selected=1, style=Style(fg="white"))

rs.on_change(lambda value: print("size:", value))
box.add(rs)
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

The open popup is rendered on the [overlay layer](layouts.md#overlays--modals), so it **floats above every other widget** (never clipped or overpainted) and the header stays a single row — opening it no longer pushes surrounding widgets down.

**Example:**

```python
from cozy_tui import Style
from cozy_tui.widgets import Dropdown, ListItem

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
from cozy_tui import Style
from cozy_tui.widgets import ProgressBar

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
from cozy_tui import Style
from cozy_tui.widgets import Table

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
from cozy_tui.widgets import Collapsible, Checkbox, ListItem

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
from cozy_tui import App
from cozy_tui.widgets import Tree

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
