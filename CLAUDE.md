# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -e .[dev]        # editable install with pytest
python -m pytest -q          # run the whole suite
python -m pytest tests/test_render.py -q          # one file
python -m pytest tests/test_render.py::test_name  # one test
python -m cozy_tui           # run the built-in demo app
python examples/<name>/<name>.py   # run an example
```

There is no linter/formatter config, but the code is `black`/`isort`-formatted (note the `# fmt: off` blocks in `events.py`).

Clipboard tests self-skip when no platform backend is available (see `tests/test_clipboard.py`); CI runs them under Xvfb/sway to exercise the X11/Wayland backends for real.

## Architecture

`cozy_tui` is a from-scratch TUI library. The only third-party dependency is `rich` (used solely to render `Markdown`/`MarkdownInput`); everything else — input parsing, clipboard, unicode width — is hand-rolled on the standard library. Targets Python 3.10+.

### Render loop (`app.py`)
`App.run()` is the single event loop. Each frame:
1. `render()` clears an in-memory cell `buffer` (a `rows × cols` grid of `Cell`), applies docks, then calls `widget.draw(self)` on every widget, then overlays.
2. Widgets paint by calling `app.write(x, y, text, style)` — the canvas is the `App` itself.
3. A **double buffer** (`_prev_cells`) enables diff rendering: `_do_diff_render()` emits VT escapes only for changed cells; `_do_full_render()` repaints everything (forced via `invalidate()` after screen switches / resize). Call `invalidate()` whenever you change something the diff can't detect.

Between frames the loop blocks in `wait_input()` (never busy-spins) and wakes for input, the cursor blink (`BLINK_INTERVAL`), terminal resize, `tick_interval`/animation frames, or worker results.

### Coordinate system
- Widget `x`/`y` are in **terminal cells**, relative to the parent (`abs_x`/`abs_y` walk the parent chain).
- Widget **sizes** passed as `"WIDTHxHEIGHT"` strings are in *virtual pixels*; divide by `App.SCALE` (10) to get cells. `Box.natural_width` = `width // scale + 2` (border eats 2 cells).
- `write()` accounts for `scroll_y` (vertical scroll of the base UI) unless an overlay is drawing (overlays are screen-fixed).

### Widgets (`cozy_tui/widgets/`, grouped by kind)
All widgets subclass `Widget` (`widget.py`) and implement `draw(canvas)`; interactive ones set `focusable = True`, handle `on_key(key)`, and expose a `cursor`/`cursor_style` for the real terminal cursor. Layout containers (`VBox`/`HBox`/`Grid`) subclass `Layout` and implement `_arrange()` to auto-position children. Package dirs: `display/`, `input/`, `layout/`, `selection/`. Public API is re-exported from `cozy_tui/__init__.py`.

### Focus & hit-testing
Tab order comes from `_collect_focusables()` → `_focusables_in()`, which **dives into focusable descendants**: a focusable container is only itself a Tab stop when it has no focusable children. Mouse `_hit_test()` walks widgets top-to-bottom, children-first, and clicking a container focuses its first focusable child (matching Tab). A modal overlay confines both Tab and mouse to itself.

Mouse events (`events.py`: `MouseClick`/`MouseDrag`/`MouseRelease`/`MouseMove`) are routed by `App._dispatch_mouse()`: click/move hit-test under the cursor, drag/release go to `self.focused` (press-to-drag capture). Widgets get `on_mouse_click`/`on_mouse_double_click`/`on_mouse_drag`/`on_mouse_release`/`on_mouse_move`/`on_mouse_enter`/`on_mouse_leave` (base no-ops firing the `on_click`/`on_drag`/`on_enter`/… registration callbacks). Double-click is synthesized in `_dispatch_click` (`DOUBLE_CLICK_INTERVAL`). Hover (`MouseMove`) requires `App(mouse_moves=True)` — it enables VT any-motion tracking (`?1003h` vs `?1002h`); the app tracks `_hovered` and dispatches enter/leave on boundary crossings. `app.on_mouse(handler)` is a global pre-dispatch hook that can consume events.

### Overlays / z-layer
`app.open_overlay(widget)` pushes onto `_overlays` (drawn above the base UI). **Modal** overlays capture all keyboard/mouse input and (with `dim`) grey the background via `_apply_backdrop()`; non-modal ones are purely visual (tooltips). `app.prompt(...)` is a one-line text-entry modal built on this. Overlays position in screen space (no scroll), re-centered each frame if `center=True`.

### Input parsing (`events.py`) & platform backend (`_console.py`)
`events.py` parses raw VT byte sequences into `Key.*` constants, `MouseClick`/`MouseDrag`, and bracketed-`Paste` events — this is the portable core. `_console.py` isolates the *only* platform-specific parts: entering raw+VT mode and blocking for input. Windows uses the Console API (`ctypes`/`kernel32`); POSIX uses `termios`/`tty`/`select`. Keep platform-specific code confined to `_console.py`.

### Unicode width (`_width.py`)
A built-in `wcwidth`-style layer: `char_width(ch)` returns 0 (combining/ZWJ — dropped by `write`), 1, or 2 (CJK/emoji — the trailing cell is blanked to stay grid-aligned). This keeps the cell grid honest without a `wcwidth` dependency.

### Background work
`app.run_worker(func, on_result=, on_error=)` runs `func` on a daemon thread; results are queued and the callbacks fire on the **main thread** from the event loop (never touch the UI from a worker thread directly).

### Clipboard (`clipboard.py`)
Built-in, no `pyperclip`. Picks a native backend per platform (Win32 API, `pbcopy`/`pbpaste`, `wl-clipboard`/`xclip`/`xsel`) with an OSC 52 fallback. `clipboard.backend()` reports the chosen one.
