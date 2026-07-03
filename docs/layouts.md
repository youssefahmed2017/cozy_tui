# Layouts, Dock & Overlays

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

See [`examples/dock_layout/dock_layout.py`](../examples/dock_layout/dock_layout.py) for a complete header / sidebar / status / fill layout.

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

See [`examples/overlay/overlay.py`](../examples/overlay/overlay.py) for a dismissable confirm dialog.

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
