# Core Concepts

### How rendering works

`cozy_tui` maintains an in-memory grid of cells (one per terminal character). Every frame, each widget writes its content into this grid via `canvas.write(x, y, text, style)`. After all widgets have drawn, the grid is serialized into ANSI escape sequences and written to stdout in one shot — this prevents flickering.

### Coordinate system

All positions are in **terminal characters** (columns and rows), not pixels. `(x=0, y=0)` is the top-left corner of the terminal.

When a widget is inside a `Box`, its `x` and `y` are **relative to the box's interior** (inside the border). The widget's absolute position is computed automatically.

### Widget lifecycle

1. You create widgets and set their properties.
2. You add them to a `Box` (or directly to `App`).
3. `App.run()` starts the event loop, which repeatedly calls `render()` → each widget's `draw()` → input handling.

### Background work & timers

`app.run_worker(func, on_result=, on_error=)` runs `func` on a daemon thread; its callbacks fire on the **main thread** from the event loop, so they can safely touch the UI.

For time-based work, the App schedules callbacks that the loop fires on the main thread (it wakes precisely when the next one is due — no busy-waiting):

- `app.after(delay, callback)` — call `callback()` once, `delay` seconds from now. Returns a handle.
- `app.every(interval, callback)` — call `callback()` repeatedly every `interval` seconds. Returns a handle.
- `app.cancel(handle)` — cancel a scheduled `after` / `every`.

These power `app.toast(...)`'s auto-dismiss. (Animating widgets like `Spinner` / `AnimatedLabel` don't need a timer — they call `canvas.request_frame(interval)` from `draw()` to keep the loop redrawing.)

---
