# Widgets

### `App`

The root of every cozy_tui application. Manages the render loop, focus, scrolling, and global key handlers.

```python
App(full=True, size="800x600", style=Style(...), catch_errors=True,
    debug=None, debug_log_path=None, default_logs=True)
```

| Parameter | Description                                                                   |
|-----------|-------------------------------------------------------------------------------|
| `full`    | `True` to use the full terminal size (recommended). `False` uses `size`.      |
| `size`    | `"WxH"` string in virtual pixels when `full=False`; divide by `App.SCALE` (10) for characters. `"800x600"` = 80 cols × 60 rows. |
| `style`   | Background style for the entire screen. Omit it to use the active [Theme](styling.md#themes)'s style instead — a fresh, independent `Style` copy, not shared between `App` instances. |
| `title`   | Terminal Tab Title (defaulted to Cozy TUI App)                                |
| `catch_errors` | An unhandled exception from `run()` shows a full-screen `TracebackView` crash view (see below) instead of propagating (terminal state is restored either way). Pass `False` for a script/test that wants `run()` to raise normally, or that has no real interactive terminal for the crash screen to block on (e.g. CI). |
| `debug` | Enables `app.debug(...)` logging and the **F12** Cozy DevTools panel. `None` (default) resolves from the `COZY_TUI_DEBUG` env var (set by `cozy-tui run --debug script.py`); an explicit `True`/`False` always overrides it. |
| `debug_log_path` | Also tail every `app.debug(...)` line to this file (only when `debug` is on) — handy for `tail -f` in a second terminal. |
| `default_logs` | When `debug` is on, `App` automatically logs its own focus changes, key presses, and mouse clicks/drags via `app.debug(...)`. Pass `False` to keep the log for your own messages only. |

**Methods:**

```python
app.add(widget)             # Add a top-level widget
app.dock(widget, side)      # Dock a widget to "left"/"right"/"top"/"bottom"/"fill"
                            # (see the Dock Layout section)
app.focus(widget)            # Set the initially focused widget
app.on_key(key, func)       # Register a global key handler
                            # Return "quit" from func to exit the app
app.quit()                  # Exit the app from anywhere (e.g. inside a callback)
app.run()                   # Start the event loop (blocking)
app.debug(*values, sep=" ")  # print()-equivalent that's safe under raw mode; no-op unless debug is on
app.toggle_devtools()        # Open/close the F12 Cozy DevTools panel yourself (menu item, button, ...)

app.confirm(message, on_yes=, on_no=)   # Yes/No modal — see layouts.md#confirmation-dialog
app.pick_file(start_dir=None, mode="file", on_select=)  # file/folder browser — see layouts.md#file-picker
app.set_tooltip(widget, text)           # hover tooltip on a widget — see the Tooltip section above

app.open_theme_palette()     # Ctrl+T by default — searchable theme picker, see styling.md#themes
app.cycle_theme()            # advance to the next built-in theme mode (not bound by default)
app.open_command_palette()   # Ctrl+P by default — searchable list of registered commands
app.register_command(name, callback, description="")  # add/override a Ctrl+P palette entry
```

**Debugging:**

```bash
cozy-tui run --debug myapp.py
```

or from code:

```python
app = App(debug=True, debug_log_path="app.log")
app.debug("connected", user.id, "at", timestamp)
```

Press **F12** for Cozy DevTools — a Chrome-style panel docked to the top-left corner with Elements (hover/click to inspect any widget, highlighted live), Console (this log, auto-scrolling as new lines arrive), Performance (FPS/timings), and Tree (the live widget hierarchy — click a node to inspect it) tabs, plus an always-visible status bar. Non-modal, so you can still interact with the rest of the app while it's open. F12 again closes it (Esc only resumes live tracking if Elements had frozen on a click).

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

### `Image`

Renders a raster image in the terminal via 2x2 "quadrant" truecolor blocks (each cell packs four source pixels, split into two representative colors and drawn with whichever of 16 Unicode Block Elements glyphs — `▘▝▖▗▀▄▌▐▚▞▛▜▙▟█` — best matches the brighter quadrants), so it reads as a recognizable picture rather than ASCII art. Requires Pillow: `pip install cozy-tui[image]` — `from cozy_tui.widgets import Image` always works without it installed; only actually loading an image raises, with that install hint.

```python
Image(x, y, source=None, *, size=None, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `source` | Optional image file path, loaded immediately |
| `size` | Optional `"WIDTHxHEIGHT"` virtual-pixel string (÷ `App.SCALE` for cells) — same convention as `Box`/`ScrollView`/`Splitter`. Without it, the image auto-fits to a default cell width with height derived from its own aspect ratio (accounting for terminal cells being ~2x taller than wide, so square/wide images aren't stretched) |
| `style` | Optional style override |

A Pillow-esque fluent builder sits alongside the constructor — every method below returns `self`:

| Method | Description |
|--------|-------------|
| `load_img(source)` | Load or replace the source image |
| `reload()` | Re-read the current source file from disk |
| `resize(size)` | Set the target cell size (`"WIDTHxHEIGHT"`) — doesn't touch the source pixels, just how many cells it's sampled down to |
| `crop(*, top=0, left=0, bottom=0, right=0)` | Trim pixels off the given edges |
| `blur(radius=2)` | Gaussian-blur the source image |
| `save(path)` | Save the current (possibly cropped/resized/blurred) image to disk |
| `render(x, y)` | Reposition the widget — drawing still happens through the normal `draw()` cycle once added to an `App` |

The Pillow work (resize + pixel sampling) only reruns when the target cell size changes or a mutator marks the image dirty — not on every frame — so an `Image` on screen costs no more than blitting a prebuilt grid of glyphs and styles.

**Example:**

```python
from cozy_tui.widgets import Image

box.add(Image(2, 2, "cat.png", size="400x300"))

# or the fluent builder:
photo = Image().load_img("cat.png").resize("400x300").render(2, 2)
box.add(photo)
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
Text(x, y, text="", *, size=None, align="left", show_border=False, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `text` | Initial text content. Use `\n` for explicit line breaks. |
| `size` | `"WIDTHxHEIGHT"` string in **character cells** (unlike `Box`/`ScrollView`, not virtual pixels) — width is the wrap column, height the visible row count, both for the inner text area. Omit to auto-size from the content. |
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

txt = Text(2, 2, size="50x10", align="left", show_border=True,
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

A focusable button that executes a callback when activated. Activates on Enter, Space, or mouse click. Its background **fades smoothly** between idle, hovered, and focused states (RGB interpolation; the idle and focused states keep their exact colours). Hover requires opting into motion (`mouse_moves=True` or an `on_enter`/`on_leave` callback).

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
btn.on_enter(func)   # Cursor entered the button (registering this enables hover)
btn.on_leave(func)   # Cursor left the button
```

**Visual states** (least → most prominent):

| State | Appearance |
|-------|-----------|
| Normal | Text centered on `bg` colored background |
| Hovered | Bold (subtle lift) |
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
btn = Button(2, 6, "Submit", width=20, style=Style(fg="white", bg="blue"))
btn.on_click(lambda b: print("Submitted!"))
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

### `DropFilesArea`

A focusable drop zone: drag a file onto the terminal (while the zone has focus) and it is filed into `storage_location`. Pasting or typing a file path and pressing **Enter** does the same thing.

```python
DropFilesArea(x, y, storage_location, size, *, move=False, hint=None,
              accept=None, on_drop=None, style=None, accent="bright_cyan")
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position in terminal characters |
| `storage_location` | Directory dropped files are placed in (created if missing) |
| `size` | `"WxH"` string in virtual pixels — divide by `App.SCALE` (10) for characters. A docked `DropFilesArea` fills its slice instead. |
| `move` | `False` (default) **copies** the dropped file; `True` **moves** it (removes the source). |
| `hint` | Prompt text shown in the zone (defaults to "Drop files here"). |
| `accept` | List of allowed extensions, e.g. `[".png", ".jpg"]` (`"png"` without the dot also works; matched case-insensitively). A dropped file whose extension isn't listed is rejected instead of stored. |
| `on_drop` | Callback fired after a drop with the list of stored `Path`s. Also settable via `drop.on_drop(func)`. |
| `accent` | Border/icon color when focused. |

A name clash **never overwrites** — the copy auto-renames to `name (1)`. File I/O runs on a background worker so a large copy won't block the UI.

For validation an extension list can't express (file size, contents, a filename pattern, …), register `drop.on_validate(func)` — called with each dropped file's `Path`; return a falsy value to reject it. If both `accept` and `on_validate` are set, a file must pass both. A drop can be part-accepted, part-rejected: accepted files are still stored and `on_drop` still fires for them, with the rejection count noted in the status line.

```python
drop = DropFilesArea(2, 2, "uploads/", "400x120", accept=[".png", ".jpg"])
drop.on_validate(lambda p: p.stat().st_size < 5_000_000)  # reject anything over 5MB
```

> **A terminal "drop" is a *path*, not a file transfer.** Terminal emulators deliver a drag-and-drop by typing the file's **path** into the input stream. `DropFilesArea` resolves that path on the **local** filesystem — the machine running the *process*. So a file dropped in a local session works, but a path dropped over an **SSH** session points at the *terminal's* machine, not the remote process, and surfaces as a friendly "not found on this machine" rather than a silent failure.
>
> Most terminals wrap the dropped path in a **bracketed paste**, which files it instantly. Some instead **type the path as raw characters** — those are buffered and filed when you press **Enter** (the zone shows the path with an "⏎ Enter to file it" prompt). `file://` URIs and quoted/escaped spaces are parsed either way.
>
> **IDE terminals swallow drops.** Embedded terminals (JetBrains/PyCharm, VS Code, …) intercept a file drop for their own editor and forward the app *nothing* — a drop won't register there (not even Shift+drop). Use a **standalone** terminal (Windows Terminal, gnome-terminal, iTerm2, …), or type/paste the path and press Enter, which works anywhere. See [interaction.md](interaction.md).

**Example:**

```python
from cozy_tui.widgets import DropFilesArea

drop = DropFilesArea(2, 2, "uploads/", "400x120")
drop.on_drop(lambda paths: status.set(f"stored {len(paths)} file(s)"))
app.add(drop)
app.focus(drop)
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

**Mouse:** clicking an item moves the cursor to it and confirms it. With `mouse_moves = True` set on the widget, hovering over an item highlights it (moves the cursor) without confirming — like arrow-key navigation.

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

**Mouse:** clicking a row moves the cursor to it and toggles it immediately. With `mouse_moves = True` set on the widget, hovering over a row highlights it (moves the cursor) without toggling.

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

**Mouse:** clicking a row moves the cursor to it and selects it immediately. With `mouse_moves = True` set on the widget, hovering over a row highlights it (moves the cursor) without selecting.

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

### `RightClickMenu` / `MenuItem` / `MenuSeparator`

A floating context menu popped up at the cursor by a right-click. You don't
`add()` it to a container — you build it once and open it from a right-click
hook with `menu.open_at(app, col, row)`, which places it as a modal overlay
(flipping left/up near screen edges).

```python
RightClickMenu(items, *, style=None)
MenuItem(text, on_select=None, *, value=None, enabled=True,
         icon=None, shortcut=None, submenu=None)
MenuSeparator()
```

| `MenuItem` arg | Description |
|----------------|-------------|
| `text` | The label. |
| `on_select` | Called with the `MenuItem` when chosen (ignored if it has a `submenu`). |
| `value` | Optional payload (defaults to `text`). |
| `enabled` | `False` dims the item and skips it during navigation. |
| `icon` | Glyph shown before the label, e.g. `"📋"`. Same as embedding it in `text`. |
| `shortcut` | Accelerator label, right-aligned (e.g. `"Ctrl+C"`). **Display only** — a hint; wire the real key with `app.on_key(...)`. |
| `submenu` | List of `MenuItem`s shown as a nested menu; the item is marked `▶`. |

- **`open_at(app, col, row)`** — open the menu with its top-left at `(col, row)`,
  as a modal overlay (flipping left/up near screen edges).
- Up/Down move the cursor (skipping separators and disabled items). Enter, a
  click, or Right selects; Esc, Left, or a click outside dismisses.
- Selecting a **leaf** closes the whole menu chain and calls its `on_select`.
  Selecting an item with a **`submenu`** opens the submenu to the side (Left/Esc
  returns to the parent).
- Icons and shortcuts are aligned by **display width**, so double-width emoji
  don't break the columns.

Pair it with [`app.on_right_click`](interaction.md#right-click--context-menus):

```python
from cozy_tui.widgets import RightClickMenu, MenuItem, MenuSeparator

menu = RightClickMenu([
    MenuItem("Copy",  icon="📋", shortcut="Ctrl+C", on_select=do_copy),
    MenuItem("Paste", icon="📄", shortcut="Ctrl+V", on_select=do_paste),
    MenuSeparator(),
    MenuItem("Theme", submenu=[
        MenuItem("Dark",  on_select=lambda i: set_theme("dark")),
        MenuItem("Light", on_select=lambda i: set_theme("light")),
    ]),
    MenuItem("Delete", icon="🗑", shortcut="Del", on_select=do_delete),
])

# Right-click anywhere pops the menu up at the cursor.
app.on_right_click(lambda col, row, widget: menu.open_at(app, col, row))
```

renders roughly as (borders drawn with box-drawing glyphs):

```
+--------------------+
| 📋 Copy    Ctrl+C  |
| 📄 Paste   Ctrl+V  |
+--------------------+
| Theme            ▶ |
| 🗑 Delete     Del  |
+--------------------+
```

---

### `MenuBar`

A horizontal row of top-level labels ("File", "Edit", …), each opening a dropdown menu built from the same `MenuItem`/`MenuSeparator` building blocks as `RightClickMenu` — a click/Down/Enter simply opens a `RightClickMenu` positioned right below the label, so submenus, icons, shortcuts, and disabled items all work the same way.

```python
MenuBar(x, y, menus, *, style=None, gap=2)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `menus` | List of `(label, items)` pairs, where `items` is whatever `RightClickMenu` accepts (a list of `MenuItem`/`MenuSeparator`) |
| `gap` | Blank columns between top-level labels (default `2`) |

Left/Right move between top-level labels; Down/Enter/Space (or a click) open the highlighted one. Once open, Esc or a click outside closes it — matching every other dropdown/menu in this library, a click that lands on a *different* label while one is already open just closes the first (a second click opens the new one).

**Example:**

```python
from cozy_tui.widgets import MenuBar, MenuItem, MenuSeparator

bar = MenuBar(0, 0, [
    ("File", [
        MenuItem("New", icon="📄", on_select=lambda it: new_file()),
        MenuSeparator(),
        MenuItem("Quit", icon="🚪", shortcut="Esc", on_select=lambda it: app.quit()),
    ]),
    ("Edit", [
        MenuItem("Copy", shortcut="Ctrl+C", on_select=lambda it: do_copy()),
    ]),
])
app.dock(bar, "top")
```

> Unlike `Box`/`Splitter`/other containers, `MenuBar`'s menus are data (`MenuItem` lists), not child widgets — so there's nothing for Tab to dive into, and `MenuBar` is always an ordinary Tab stop.

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

### `Slider`

A draggable numeric control — the interactive counterpart to `ProgressBar`. Click or drag anywhere on the track to jump the handle straight there; when focused, arrow keys nudge it.

```python
Slider(x, y, minimum=0, maximum=100, value=None, step=1, *,
       width=20, page_step=None, show_value=True, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position |
| `minimum`, `maximum` | Range bounds (int or float; `minimum` must be `<= maximum`) |
| `value` | Initial value (default: `minimum`) |
| `step` | Amount Left/Right/Up/Down move by |
| `width` | Total width in characters, including the value label when `show_value=True` |
| `page_step` | Amount PageUp/PageDown move by. Defaults to `max(step, (maximum - minimum) // 10)`. |
| `show_value` | Draw the current value right of the track (`True` by default) |

**Reading / setting the value:**

```python
s.get()                 # current value
s.set(value)            # set directly (clamped to minimum–maximum)
s.increment(amount=None)  # += step (or amount)
s.decrement(amount=None)  # -= step (or amount)
```

**Callbacks:**

```python
s.on_change(func)   # func(value) — fires when the value actually changes (not on a clamp that leaves it unchanged)
```

**Key bindings (when focused):** Left/Down — decrement, Right/Up — increment, Page Up/Down — jump by `page_step`, Home/End — jump to `minimum`/`maximum`.

**Mouse:** click or drag anywhere on the track jumps the handle to that position, snapped to the nearest `step`.

Floats work the same as ints — the value label's width is reserved from whichever of `minimum`/`maximum`/`step` needs the most decimal places, so the bar never jitters as the value's printed width changes.

**Example:**

```python
from cozy_tui.widgets import Slider

volume = Slider(2, 2, minimum=0, maximum=100, value=70, step=1, width=30)
volume.on_change(lambda v: status.set_text(f"volume: {v}"))
box.add(volume)
```

---

### `Splitter`

Two panes divided by a 1-cell bar you can drag to resize them. `orientation="horizontal"` (default) places the panes side by side with a vertical bar; `"vertical"` stacks them with a horizontal bar.

```python
Splitter(x, y, size, first, second, *,
         orientation="horizontal", ratio=0.5, min_size=1, step=1, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `size` | `"WIDTHxHEIGHT"` in virtual pixels — ÷ `App.SCALE` (10) for cells, like `Box`. A **docked** `Splitter` fills its slice instead. |
| `first`, `second` | The two pane widgets. Each is resized every frame via its own `dock_resize(w, h, scale)`, so panes built from `Box`/`ScrollView`/another `Splitter` grow to fill their share; fixed-size widgets keep their own size and are simply clipped to it. |
| `orientation` | `"horizontal"` (side by side) or `"vertical"` (stacked) |
| `ratio` | Initial split, `0.0`–`1.0` (default `0.5`, i.e. even) |
| `min_size` | Minimum cells either pane can be squeezed to |
| `step` | Cells the keyboard nudges the bar by |

**Reading / setting the split:**

```python
splitter.get_ratio()        # current split, 0.0-1.0
splitter.set_ratio(ratio)   # set directly (clamped)
```

**Keyboard (once the bar itself is focused):** Left/Right (horizontal) or Up/Down (vertical) nudge the bar by `step`; Home/End snap it to the `min_size` extent on either side.

**Mouse:** drag the bar to resize freely.

> **Tab dives into whichever pane has focusable content first**, matching every other container in this library — so if either pane holds something focusable, Tab never stops on the bar itself; click it directly to grab it for the keyboard. When neither pane has anything focusable, the bar becomes an ordinary Tab stop.

**Example:**

```python
from cozy_tui.widgets import Box, Splitter

left = Box(0, 0, "1x1", title="Files", border="rounded")
right = Box(0, 0, "1x1", title="Preview", border="rounded")
splitter = Splitter(0, 0, "1x1", left, right, min_size=20)
app.dock(splitter, "fill", margin=1)
```

> `"1x1"` placeholder sizes are normal here — a docked (or `Splitter`-paned) `Box` grows to fill whatever slice it's assigned via `dock_resize`, so the constructor size never actually applies.

---

### `Spinner`

A small animated activity indicator — the idiomatic "working…" companion to `run_worker`. Non-focusable; show one while a background task runs and remove it in the worker's `on_result`. It animates smoothly on its own (via `request_frame`), so the app does **not** need `tick_interval` set.

```python
Spinner(x, y, *, frames=None, speed=None, spinner="dots", label="", style=None)
```

| Parameter | Description |
|-----------|-------------|
| `spinner` | Name of a built-in animation — picks both `frames` and `speed` in one shot. One of: `dots` (default), `line`, `normalDots`, `growVertical`, `bounce`, `arrow`, `bouncingBar`, `bouncingBall`, `clock`, `material`, `moon`, `pong`, `aesthetic`. Raises `ValueError` on an unknown name. |
| `frames` | Iterable of frame strings for a fully custom animation, overriding `spinner`. The old class-attribute presets still work too: `Spinner.DOTS`, `LINE`, `BAR`, `MOON`, `ARROW`. |
| `speed` | Seconds per frame. Defaults to the chosen preset's speed (or `0.08` with custom `frames`); pass it explicitly to override either. |
| `label` | Optional text drawn after the spinner glyph. |

**Example:**

```python
from cozy_tui.widgets import Spinner

spinner = Spinner(2, 2, label="Loading…")
box.add(spinner)
app.run_worker(fetch, on_result=lambda data: box.children.remove(spinner))

Spinner(2, 4, spinner="material", label="Uploading…")
```

Run `python -m cozy_tui.spinners` for a live showcase of every preset.

---

### `Toast` / `app.toast`

A transient notification that pops in a screen corner, stacks with other toasts, and auto-dismisses on a timer. Usually created via **`app.toast(...)`** rather than constructed directly — it's non-modal, so it never steals focus or blocks input.

```python
app.toast(message, *, level="info", duration=3.0, icon=None, corner="bottom-right")
```

| Parameter | Description |
|-----------|-------------|
| `message` | Text shown in the toast. |
| `level` | `"info"` / `"success"` / `"warning"` / `"error"` — picks the accent color from the active [Theme](styling.md#themes) (`theme.info`/`success`/`warning`/`error`) and a default icon (ℹ / ✓ / ⚠ / ✗). |
| `duration` | Seconds before it auto-dismisses. `0` makes it sticky (no timer). |
| `icon` | Override the level's default icon. |
| `corner` | `"bottom-right"` (default), `"bottom-left"`, `"top-right"`, `"top-left"`. |

Auto-dismissal is driven by the App's timer primitives (`app.after` / `app.every`), which the event loop fires on the main thread — see [concepts.md](concepts.md).

**Example:**

```python
app.toast("Saved successfully.", level="success")
app.toast("Upload failed.", level="error", duration=5.0)
```

---

### `Tooltip` / `app.set_tooltip`

A small floating one-line text bubble anchored to another widget, shown on hover. Usually created via **`app.set_tooltip(...)`** rather than constructed directly — like `Toast`, it's non-modal and non-focusable, so it never steals focus or blocks input; whatever's under it stays fully interactive while it's showing.

```python
app.set_tooltip(widget, text, *, delay=0.4)
```

| Parameter | Description |
|-----------|-------------|
| `widget` | The widget to anchor the tooltip to and watch for hover. |
| `text` | The tooltip's text. |
| `delay` | Seconds the mouse must stay over `widget` before the tooltip shows (default `0.4`) — a quick pass-through never flashes one. |

Position is recomputed every frame from `widget`'s current position — right below it by default, flipped above/clamped left if that would run off the screen edge — so it tracks a moving or resizing anchor correctly.

`set_tooltip` wires `widget.on_enter`/`on_leave` under the hood (see [Hover / motion events](interaction.md#hover--motion-events)), which also opts `widget` into hover tracking — so it replaces any enter/leave handler already registered on that widget (each is a single callback slot, like `on_click`).

**Example:**

```python
save_btn = Button(2, 10, "Save").on_click(save)
box.add(save_btn)
app.set_tooltip(save_btn, "Write the current file to disk")
```

---

### `TracebackView` / `crash_screen.show_traceback`

Displays an exception's traceback with Rich's syntax highlighting and local-variable inspection, rendered into the cell grid like any other widget (not a stdout print) — so it composes with `ScrollView`, overlays, and the raw-mode/alt-screen renderer. Non-focusable and non-interactive on its own; wrap it in a `ScrollView` for tracebacks taller than the screen (`show_locals` in particular can make these long).

```python
TracebackView(x, y, width, exc, *, show_locals=True, style=None)
```

| Parameter | Description |
|-----------|-------------|
| `width` | Wrap width in character cells (matches `Markdown`'s convention — not virtual pixels like `Box`/`ScrollView`). |
| `exc` | The exception instance to display. |
| `show_locals` | Include each frame's local variables (Rich's `show_locals`). |

**Example:**

```python
from cozy_tui.widgets import ScrollView, TracebackView

try:
    risky()
except Exception as exc:
    view = ScrollView(2, 1, "700x400")
    view.add(TracebackView(0, 0, 68, exc))
    app.add(view)
```

For the common case — a ready-made full-screen crash view (Esc quits, C copies the plain-text traceback to the clipboard, arrows/PageUp/PageDown/Home/End scroll) — use `show_traceback` instead of building the screen yourself. **`App` already does this automatically**: an unhandled exception from `app.run()` calls `show_traceback` for you (see `catch_errors` in the `App` section above), so most code never needs to call it directly — it's there for scripts that catch an exception outside of `run()` (or that want the screen without an `App` at all):

```python
from cozy_tui.crash_screen import show_traceback

try:
    risky()
except Exception as exc:
    show_traceback(exc)
```

`cozy_tui.widgets.display.traceback_view.format_traceback(exc)` returns the plain-text traceback (no styling) if you want it for logging without building a widget at all. Run `python -m cozy_tui.crash_screen` for a demo.

`show_traceback`'s own `App` always runs with `catch_errors=False` — if the crash screen itself fails, it fails loudly rather than recursively trying to show a crash screen for its own crash.

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

### `Tabs`

A tabbed container: a strip of clickable tab titles above a content area showing the active tab's panel. Only the active panel is drawn, focusable, and hit-tested — inactive tabs are inert.

```python
Tabs(x, y, size, *, style=None, accent="bright_cyan", animate=True, anim_duration=0.18)
```

| Parameter | Description |
|-----------|-------------|
| `x`, `y` | Position in terminal characters |
| `size` | `"WIDTHxHEIGHT"` in virtual pixels — divide by `App.SCALE` (10) for cells, like `Box`. A **docked** `Tabs` fills its slice instead. |
| `style` | Style for the tab area (its `bg` fills the panel background) |
| `accent` | Color of the active tab + its underline (default `"bright_cyan"`) |
| `animate` | Glide the underline on switch and reveal the new panel when it finishes (`True` by default; `False` = instant swap / reduced motion). |
| `anim_duration` | Seconds the switch animation takes. |

**Switch animation:** switching tabs smoothly glides the accent underline from the old title to the new one (ease-out, ~30fps); the content area stays empty during the glide and the new panel is revealed only when the animation finishes. It's purely visual — `active`, focus, and hit-testing switch immediately — and self-drives the redraw (no `tick_interval` needed). `animate=False` disables it.

**Building tabs:** `add_tab(title, *widgets)` adds a tab and returns its **panel** (a container) so you can add more widgets to it. Widgets passed inline are placed in the panel immediately.

```python
from cozy_tui.widgets import Tabs, Label, ListView, Input

tabs = Tabs(2, 2, "600x200")

files = tabs.add_tab("Files")            # returns the panel container
files.add(ListView(1, 1, ["a", "b"], height=4))

tabs.add_tab("Settings", Input(1, 1, 20))  # widgets can be passed inline
tabs.add_tab("About", Label(1, 1, "cozy_tui"))

tabs.on_change(lambda index: ...)        # fires with the new tab index
box.add(tabs)
```

**Focus & navigation:** keyboard focus lands on the tab **strip** first — Left/Right (or Home/End) switch tabs; pressing **Tab** again dives into the active panel's own controls. A **click** on a tab title switches to it. Pass `tabs.bar` to `app.focus(...)` to start focus on the tabs.

**Methods / properties:** `select(index)` (clamped, fires `on_change`), `panel(index)`, `bar`, `selected_index`, `selected_title`.

---

### `ScrollView`

A scrollable viewport. Add widgets whose combined height exceeds the box; only the visible slice is drawn (clipped to the viewport), with a Textual-style **scrollbar** on the right edge. Child `y` positions are in **content space** (`0` = top of the content, may exceed the viewport height).

```python
ScrollView(x, y, size, *, autoscroll=True, scrollbar=True, smooth=True, style=None, accent="bright_cyan")
```

| Parameter | Description |
|-----------|-------------|
| `size` | `"WxH"` string in virtual pixels — ÷ `App.SCALE` (10) for the viewport's cell size. A docked ScrollView fills its slice. |
| `autoscroll` | `True` (default) keeps the view pinned to the **bottom** as content grows — ideal for logs — until the user scrolls up (which unpins); scrolling back to the bottom re-pins. |
| `scrollbar` | Show the scrollbar on the right edge (`True` by default; auto-hides when content fits). |
| `smooth` | `True` (default) eases the displayed offset toward the target (momentum scrolling, ~30fps); `False` snaps instantly. |
| `accent` | Color of the scrollbar thumb. |

**Scrolling:** mouse **wheel** or the keyboard (↑/↓, PageUp/PageDown, Home/End) while focused, or **drag the scrollbar thumb**. When a `ScrollView` has focus it consumes the wheel/page keys (otherwise they scroll the whole base UI).

**Methods:** `add(widget)` (content-space `(x, y)`; returns it), `clear()`, `scroll_to(offset)`, `scroll_by(delta)`, `scroll_to_top()`, `scroll_to_bottom()`, `content_height(scale)`.

> **Note:** best suited to display/scrolling content (text, logs, long read-only forms). Focusable children inside a `ScrollView` become the Tab stops (so the view itself isn't), and clipped-out children keep their hit-boxes — so interactive controls in a scrolled region are a v1 caveat.

**Example:**

```python
from cozy_tui.widgets import ScrollView, Label

log = ScrollView(2, 2, "600x160", autoscroll=True)
for i in range(200):
    log.add(Label(0, i, f"line {i}"))
app.add(log)
app.focus(log)
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
