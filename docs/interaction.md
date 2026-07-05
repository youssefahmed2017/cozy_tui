# Input & Interaction

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
`DELETE`, `INSERT`, `PAGE_UP`, `PAGE_DOWN`,
`CTRL_UP`, `CTRL_DOWN`, `CTRL_LEFT`, `CTRL_RIGHT`, `CTRL_C`,
`F1`–`F12`

**Modifier combos.** Terminals only send Alt/Ctrl combined with another key, so use the helpers:

```python
from cozy_tui.events import Key

app.on_key(Key.alt("s"), save)          # Alt+S   → "alt+s"
app.on_key(Key.ctrl("f"), find)         # Ctrl+F  → the raw control byte "\x06"
app.on_key(Key.F5, refresh)             # F5
app.on_key(Key.ctrl(Key.F5), hard_refresh)  # Ctrl+F5 → "ctrl+F5"

# Key.ALT == "alt" and Key.CTRL == "ctrl" are the underlying prefixes.
```

- `Key.alt(c)` → `"alt+" + c` (matches `read_key()` for `Alt+<char>`, e.g. `Key.alt("backspace")`).
- `Key.ctrl(c)` → the actual control byte for a **letter** (`Key.ctrl("a") == Key.CTRL_A`), or a `"ctrl+<key>"` string otherwise (e.g. an F-key).
- `Key.shift(c)` → `"shift+" + c` (used for F-keys).
- **Modified F-keys** parse to canonical `"ctrl+F5"`, `"shift+F5"`, `"ctrl+shift+F12"` … The modifier order is always `ctrl`, `alt`, `shift`, and the helpers compose in that order — `Key.ctrl(Key.shift(Key.F5)) == "ctrl+shift+F5"`.

---

## Mouse Support

Mouse clicks are handled automatically:

- **Click any focusable widget** → gives it focus
- **Click a Button** → gives it focus and activates it
- **Click a Checkbox** → gives it focus and toggles it
- **Scroll wheel** → scrolls the app content up/down

No extra setup needed — mouse support is enabled automatically when `app.run()` starts.

### Per-widget mouse callbacks

Any widget can register callbacks for the different mouse gestures. `on_click`
also fires on keyboard activation; the rest are mouse-only:

```python
widget.on_click(lambda w: ...)              # click or keyboard activation
widget.on_right_click(lambda w, col, row: ...)  # right button (see below)
widget.on_double_click(lambda w: ...)       # two clicks within 0.4s
widget.on_drag(lambda w, col, row: ...)     # motion while a button is held
widget.on_release(lambda w, col, row: ...)  # button released
widget.on_hover(lambda w, col, row: ...)    # motion with no button (see below)
widget.on_enter(lambda w: ...)              # cursor entered the widget
widget.on_leave(lambda w: ...)              # cursor left the widget
```

`on_click` is the activation hook for simple controls — `Button`, `Checkbox`,
`Hyperlink`. The **selection widgets** (`ListView`, `CheckList`, `RadioSet`,
`Dropdown`, `Table`, `Tree`) have their own, more specific callbacks that carry
the selected value — prefer those over `on_click`:

```python
list_view.on_select(lambda value: ...)   # Enter or click on a row
check_list.on_toggle(lambda value, checked: ...)
radio_set.on_change(lambda value: ...)   # selection changed
```

`col`/`row` are absolute terminal cells (already adjusted for scrolling). If you
subclass a widget instead, override `on_mouse_click` / `on_mouse_right_click` /
`on_mouse_double_click` / `on_mouse_drag` / `on_mouse_release` / `on_mouse_move` /
`on_mouse_enter` / `on_mouse_leave` — the override replaces the default, so call
the matching `_fire_*` if you still want the registered callback to run. A
double-click with no `on_double_click` handler falls back to firing the normal
click.

### Right-click / context menus

A right-click (button 2) is routed on its own path: it **never** moves focus or
fires the normal `on_click`, so right-clicking a button doesn't press it. Two
ways to handle it:

```python
# Global — fires with the widget under the cursor, or None over empty space.
app.on_right_click(lambda col, row, widget: ...)   # return True to consume

# Per-widget — only when the right-click lands on that widget.
widget.on_right_click(lambda w, col, row: ...)
```

The global hook runs first; if it returns `True` the per-widget handler is
skipped. This is the intended way to pop up a
[`RightClickMenu`](widgets.md#rightclickmenu--menuitem--menuseparator):

```python
from cozy_tui.widgets import RightClickMenu, MenuItem

menu = RightClickMenu([
    MenuItem("Copy",  on_select=lambda i: do_copy()),
    MenuItem("Paste", on_select=lambda i: do_paste()),
])
app.on_right_click(lambda col, row, w: menu.open_at(app, col, row))
```

> **Terminal caveat:** right-click only reaches the app in **standalone**
> terminals (Windows Terminal, gnome-terminal, kitty, iTerm2, …). **Embedded /
> IDE terminals** (VS Code, JetBrains, …) bind the right button to their *own*
> context menu and swallow it before it hits the app's mouse-reporting stream,
> so `on_right_click` never fires there. Motion and left-click still come
> through, so hover and normal clicks work regardless. Some IDE terminals
> forward the button on **Shift+right-click**, but that's terminal-dependent and
> outside the library's control — if you need a menu everywhere, also expose a
> keyboard or button trigger that calls `menu.open_at(...)`.

### Hover / motion events

Bare mouse motion (no button held) is **off by default** because any-motion
tracking floods the input stream on every cursor move. It's opt-in **per
widget**, not app-wide: a widget receives `on_hover` / `on_mouse_move` /
`on_enter` / `on_leave` only when its `mouse_moves` flag is set.

```python
w = MyWidget(..., mouse_moves=True)   # subclasses can pass it through to Widget
w.on_hover(lambda widget, col, row: ...)  # registering also flips mouse_moves on
```

Registering any of `on_hover` / `on_enter` / `on_leave` sets `mouse_moves`
automatically, so most code never touches the flag directly. Built-in
interactive widgets that use hover — `Button`, `ListView`, `CheckList`,
`RadioSet`, `RightClickMenu` — opt in themselves.

The App enables terminal-level motion tracking (`?1003h`) automatically whenever
at least one live widget wants it — including overlays opened mid-run, like a
`RightClickMenu` — and stays on the cheaper drag-only mode otherwise. There is no
app-wide `mouse_moves` switch.

`on_enter` / `on_leave` fire once as the cursor crosses a widget's boundary (the
app tracks which widget is hovered and dispatches the transitions), which is what
drives, e.g., `Button`'s hover state.

### Global mouse hook

Register an app-wide hook to see every mouse event before it reaches a widget.
Return `True` to consume the event and skip the default dispatch:

```python
def on_mouse(event):   # MouseClick | MouseDrag | MouseRelease | MouseMove
    ...
    return False       # let it through to the widget under the cursor

app.on_mouse(on_mouse)
```

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
