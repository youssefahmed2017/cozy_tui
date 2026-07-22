# Core Concepts

### How rendering works

`cozy_tui` maintains an in-memory grid of cells (one per terminal character). Every frame, each widget writes its content into this grid via `canvas.write(x, y, text, style)`. After all widgets have drawn, the grid is serialized into ANSI escape sequences and written to stdout in one shot — this prevents flickering.

### Coordinate system

All positions are in **terminal characters** (columns and rows), not pixels. `(x=0, y=0)` is the top-left corner of the terminal.

When a widget is inside a `Box`, its `x` and `y` are **relative to the box's interior** (inside the border). The widget's absolute position is computed automatically.

### Clipping

`canvas.push_clip(x0, y0, x1, y1)` confines subsequent `write()` calls to the rectangle `[x0, x1) × [y0, y1)` (absolute content coordinates) until the matching `canvas.pop_clip()`. Calls nest — always balance a `push_clip` with a `pop_clip`, typically wrapping a container's call to `child.draw(canvas)`. `ScrollView` uses this to clip its content to the visible viewport.

### Widget lifecycle

1. You create widgets and set their properties.
2. You add them to a `Box` (or directly to `App`).
3. `App.run()` starts the event loop, which repeatedly calls `render()` → each widget's `draw()` → input handling.

Everything below works at any point after step 2 — while the app is running, from a key handler, a timer, or a worker's `on_result`.

#### Removing widgets

```python
app.remove(widget)      # anywhere in the tree; returns it, or None if absent
container.remove(child) # a Box / VBox / HBox / Grid / ScrollView you already hold
container.clear()       # every child at once
```

**Prefer `app.remove(...)`.** It searches the whole tree *and* moves focus off whatever it takes away. A removed widget that is still `app.focused` keeps receiving every keystroke while being invisible and unreachable by Tab — a UI that silently stops responding, which is much harder to diagnose than a missing widget. Focus lands on the next remaining stop, the same place Tab would have gone.

#### Hiding and disabling

Every widget has two flags, both plain attributes you can flip at any time:

| Flag | Drawn? | Focusable / clickable? | Layout |
|---|---|---|---|
| `visible = False` | no | no — subtree and all | collapses (see below) |
| `disabled = True` | yes, dimmed | no | unchanged |

```python
submit.disabled = not form_is_valid()
advanced_panel.visible = show_advanced
```

Three things worth knowing:

- **Hiding collapses the gap.** In a `VBox`/`HBox`, a hidden child measures as nothing and takes its surrounding `gap` with it, so the stack closes up instead of leaving a hole. (`Grid` keeps its slot — reflowing a grid around a hidden cell would move everything else.)
- **`disabled` dims automatically.** `widget.style` returns a dimmed copy while the flag is set, so every widget gets the look without knowing the flag exists. Set an explicit `style` and it's dimmed from that.
- **A disabled widget still swallows clicks.** It occupies its cells, so a click dies there rather than falling through to whatever is behind it. A *hidden* one is fully transparent to the mouse.

A disabled **container** is inert itself but still lets Tab reach its children — the container is what's disabled, not its contents.

#### Focus events

```python
email.on_blur(lambda w: show_error(w.value) if not valid(w.value) else None)
email.on_focus(lambda w: hide_error())
```

`on_blur` is the standard place to validate a field: it fires once the user is done with it, rather than on every keystroke. Both handlers run *after* `app.focused` has been updated, so a handler that inspects it sees the final state. Re-focusing the widget that already has focus fires nothing.

### Screens

A screen is a **named set of top-level widgets** — a menu, a game, a game-over panel. Switching swaps which set the app draws.

```python
menu = app.screen("menu")            # get-or-create
menu.add(Label(2, 2, "PAUSED"))
menu.dock(footer, "bottom")

game = app.screen("game")
game.add(board)

app.show("menu")                     # or app.show(menu)
```

There's no `Screen` subclass to write and no routing table: `screen.add` / `screen.dock` / `screen.focus` are the same three calls you already make on `App`. A screen *is* what `app.widgets` holds, given a name so there can be more than one.

**Screens keep their widgets.** Switching away and back leaves a half-typed form, a scroll position, and the focused widget exactly as they were — nothing is rebuilt. That's why a screen is a list rather than a `build()` function: rebuilding on every switch would be simpler to implement and would silently throw away state the user cares about.

| | |
|---|---|
| `app.screen(name)` | Get or create a screen |
| `app.show(name_or_screen)` | Switch to it; returns it. `KeyError` on an unknown name |
| `app.current_screen` | The showing `Screen`, or `None` if the app doesn't use screens |
| `screen.add` / `dock` / `remove` / `focus` | As on `App`, scoped to this screen |
| `screen.on_show(f)` / `screen.on_hide(f)` | Fired on each switch in / out; `f(screen)` |
| `screen.on_key(key, f, description=, section=)` | A binding that applies only while this screen shows, and **wins over** the app-wide binding for that key |
| `screen.widgets`, `screen.name`, `screen.is_current` | |

Three details:

- **The first screen adopts whatever the app already had**, so you can introduce screens to an existing app without blanking it or reordering your setup code.
- **Tab is confined to the showing screen** — the others aren't in the tree at all.
- **`screen.on_key` beats `app.on_key`** for the same key while that screen shows, so Esc can mean "back" on one screen and "quit" on another with no dispatcher in the middle:

  ```python
  login.on_key(Key.ESC, lambda: app.show(menu))
  menu.on_key(Key.ESC, app.quit)
  ```
- **Not using screens costs nothing.** `app.widgets` behaves exactly as it always has until `app.screen(...)` is called for the first time.

```python
def game_over(score):
    app.screen("over").add(Label(2, 2, f"Score: {score}"))
    app.show("over")

app.on_key("m", lambda: app.show("menu"))
```

### Background work & timers

`app.run_worker(func, on_result=, on_error=)` runs `func` on a daemon thread; its callbacks fire on the **main thread** from the event loop, so they can safely touch the UI.

For time-based work, the App schedules callbacks that the loop fires on the main thread (it wakes precisely when the next one is due — no busy-waiting):

- `app.after(delay, callback)` — call `callback()` once, `delay` seconds from now. Returns a handle.
- `app.every(interval, callback)` — call `callback()` repeatedly every `interval` seconds. Returns a handle.
- `app.cancel(handle)` — cancel a scheduled `after` / `every`.

These power `app.toast(...)`'s auto-dismiss. (Animating widgets like `Spinner` / `AnimatedLabel` don't need a timer — they call `canvas.request_frame(interval)` from `draw()` to keep the loop redrawing.)

### Reactive state (`cozy_tui.state`)

A `State` is an observable value. Bind one to a widget property and the widget follows it — no manual "update the label too" bookkeeping, and no special reactive widgets.

```python
from cozy_tui import State
from cozy_tui.widgets import Box, Label

title = State("Downloads")

app.add(Label(2, 1, title))
app.add(Box(2, 3, "400x100", title=title))

title.value = "Downloads (3)"   # both update
```

Assignment is the API: `s.value = x` notifies. `s.set(x)` is the same thing as a callable (handy in a lambda or as a ready-made callback slot), and `s.update(fn)` sets the value to `fn(current)` — `count.update(lambda n: n + 1)`.

**Reactive properties.** Any of these constructor arguments accepts a `State` in place of a plain value:

| Widget | Reactive properties |
|---|---|
| `Label`, `Button`, `Checkbox` | `text` |
| `Hyperlink` | `text`, `link` |
| `Box` | `text`, `title` |
| `Text` | `text` (re-wraps on change) |
| `ProgressBar` | `progress` (clamped on change) |

A plain value passed to any of them behaves exactly as it always has — nothing is subscribed and nothing is tracked. Reactivity is strictly opt-in by wrapping the value in `State(...)`; a bare `name = "HELLO"` never becomes reactive.

**Subscribing directly.** For anything not on that table, listen yourself:

```python
status = State("idle")
status.subscribe(lambda v: app.toast(f"Now: {v}"))     # returns the callback
status.bind(some_object, "attr")                       # keep an attribute in sync
```

`State.bind(obj, attr)` (and every widget binding, which is built on it) holds `obj` **weakly** — a discarded widget drops its own subscription, so a long-lived `State` in an app that spawns and destroys widgets doesn't accumulate listeners.

**When the screen actually updates.** Notification is synchronous: by the time the assignment returns, every bound attribute is already updated. The repaint is just the loop's ordinary next frame, which follows key/mouse dispatch, a timer callback, and a worker's `on_result` — the four places your code normally runs — and the diff renderer emits only the cells that changed. Setting a `State` directly from a background thread updates the attributes but won't schedule a frame; pass the value back through `run_worker(on_result=...)`, the same rule that already applies to touching widgets from a thread.

Setting a value equal to the current one is dropped, so re-assigning the same string doesn't fan out a needless update.

Binding is **one-way** (state → widget) by design. An `Input`'s typed text does not write back into a `State`; use `input.on_change(state.set)` when you want that, so the write-back stays visible in the code rather than implied.

---

### Motion primitives (`cozy_tui.motion`)

Smooth animations share a small toolkit:

- **Easing curves** — `linear`, `ease_in`, `ease_out`, `ease_in_out`, `ease_out_quad` (each maps `t` in `[0,1]` to an eased `[0,1]`).
- **Interpolation** — `lerp(a, b, t)` for scalars; `lerp_color(c0, c1, t)` blends two RGB colours (rgb tuple / `#hex` / `rgb(...)`) into an `"rgb(r,g,b)"` string. Colour is the one thing a cell grid animates *truly* smoothly.
- **`Tween(start, end, duration, easing=ease_out)`** — eases a scalar over time off a wall clock (no external ticking). A widget reads `tween.value()` each frame and calls `canvas.request_frame(...)` until `tween.done`.

```python
from cozy_tui.motion import Tween, ease_out, lerp_color

self._t = Tween(0, 1, 0.15, ease_out)     # in __init__
# in draw():
bg = lerp_color("#333", "#0af", self._t.value())
if not self._t.done:
    canvas.request_frame(0.033)
```

`Tabs` (switch glide) and `ScrollView` (momentum scrolling) are both built on this.

---
