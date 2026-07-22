# Layouts, Dock & Overlays

## Layouts

Layouts are borderless containers that **automatically position their children** — you don't set `x`/`y` on children added to a layout. They inherit from `Widget` and can be placed anywhere a widget can (inside a `Box`, directly on `App`, or nested inside other layouts).

All layouts support `.add(widget, flex=0)` which returns `self` for chaining — `VBox`/`HBox` only, see [Flex growth](#flex-growth-flex) below.

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
from cozy_tui import Style
from cozy_tui.widgets import VBox, Label, Button

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
from cozy_tui import Style
from cozy_tui.widgets import HBox, Button

hbox = HBox(2, 10, gap=2)
hbox.add(Button(0, 0, "OK", width=10, style=Style(fg="white", bg="green")))
hbox.add(Button(0, 0, "Cancel", width=10, style=Style(fg="white", bg="red")))
box.add(hbox)
```

---

### Flex growth (`flex=`)

By default every child keeps its own natural size (`flex=0`) and `VBox`/`HBox` shrink to fit them, exactly as above. Pass `flex=N` (an integer `> 0`) to `.add()` to instead have that child **grow** to help fill the layout, proportional to its weight against every other flex-marked sibling:

```python
sidebar = VBox(0, 0)
sidebar.add(Label(0, 0, "Files"))          # flex=0: stays its natural size
sidebar.add(file_list, flex=1)             # flex=1: grows to fill what's left
sidebar.add(status_bar)                    # flex=0: stays pinned right after file_list

app.dock(sidebar, "left", margin=1)
```

**This only does anything once the layout itself has a known target size** — i.e. it's been docked (`app.dock(...)`/`box.dock(...)`) with a side other than its own natural fit, most usefully `"fill"`. An un-docked (or non-`"fill"`-docked without room to spare) `VBox`/`HBox` has no "leftover space" concept, so `flex=` children just render at their natural size, same as `flex=0` — harmless, not an error.

Multiple flex children split whatever's left over **proportional to weight** (`flex=1` and `flex=2` split it 1:3 and 2:3), after every `flex=0` sibling's natural size and every gap (`gap=`, counted between *all* children, flex or not) is subtracted first. A child never shrinks below its own natural size — if the fixed children already exceed the layout's target size, flex children just get zero extra rather than going negative.

`Grid` doesn't implement flex distribution — `flex=` is accepted (inherited from the shared `Layout.add()`) but silently ignored, same as an un-docked `VBox`/`HBox`.

See [`_internal/textmesser.py`](../_internal/textmesser.py) for a worked example: a `flex=1` spacer `Label` between a status line and a Quit button pins Quit to the bottom of its `Box`, live, as the pane is resized by dragging the `Splitter`.

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
from cozy_tui.widgets import Grid, Checkbox

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

See [`examples/dashboard/dashboard.py`](../examples/dashboard/dashboard.py) for a docked header / footer / fill layout.

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

See [`examples/deploy/deploy.py`](../examples/deploy/deploy.py) for a dismissable confirm dialog built this way, alongside the `app.confirm()`/`app.prompt()` versions of the same guard.

> **Why these are one self-contained widget, not composed from smaller ones.** A modal overlay routes *every* key to a single focused widget — there's no bubbling if that widget doesn't handle a key. So `PromptDialog`/`ConfirmDialog`/`FilePicker` (below), and the search palettes in [styling.md](styling.md#themes) and [interaction.md](interaction.md#command-palette), each implement their own text buffer and navigation directly rather than composing a real `Input` with a `ListView` inside one modal — that composition would need a hand-written wrapper deciding "is this a nav key → the list, else → the Input" anyway, for no less code than doing it directly.

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

### Confirmation dialog

For "ask a Yes/No question", `app.confirm()` wraps `ConfirmDialog` the same way `app.prompt()` wraps `PromptDialog`:

```python
app.confirm("Delete this file?", default=False,
            on_yes=lambda: delete(file),
            on_no=lambda: None)
```

```python
app.confirm(message, *, on_yes=None, on_no=None, yes_label="Yes", no_label="No",
            default=True, width=40, close_on_click_outside=True)  # returns the ConfirmDialog
```

Left/Right (or Tab/Shift+Tab) move between the two buttons, Enter picks the highlighted one, `Y`/`N` pick directly, a click picks whichever button it lands on. Cancelling — Esc or a click outside — calls `on_no()` too, since "didn't confirm" should behave like "said no" for anything gated behind a confirmation.

### File picker

For "let the user browse to a file or folder", `app.pick_file()` wraps `FilePicker`:

```python
app.pick_file(mode="file", extensions=(".png", ".jpg"),
              on_select=lambda path: load_image(path))
```

```python
app.pick_file(start_dir=None, *, mode="file", extensions=None, on_select=None,
              on_cancel=None, width=60, height=10, close_on_click_outside=True)  # returns the FilePicker
```

Opens rooted at `start_dir` (defaults to the current working directory). Type to filter entries *in the current directory* (not recursive, same live-filter pattern as the search palettes); Up/Down/Home/End move the cursor; Enter or a click on a directory (or `..`) navigates into it, on a file (`mode="file"`) picks it and closes. `mode="directory"` shows a "· Select this folder ·" entry instead of listing files, since otherwise there'd be no way to pick a directory without descending into it forever. `extensions` (e.g. `(".py", ".md")`) restricts which files are shown in file mode. A directory that can't be listed (permissions, or something deletes it mid-browse) shows a dimmed message instead of crashing — `..` stays available so you can back out. `on_select(path)` fires with a `pathlib.Path`; cancelling (Esc / click outside) fires `on_cancel()`.

---
