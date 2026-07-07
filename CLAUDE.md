# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -e .[dev]        # editable install with pytest
python -m pytest -q          # run the whole suite
python -m pytest tests/test_render.py -q          # one file
python -m pytest tests/test_render.py::test_name  # one test
python -m cozy_tui           # run the built-in demo app (no subcommand → demo)
cozy-tui doctor              # CLI: environment checks; also `demo`, `info`, `--version`
cozy-tui run script.py       # run a script, like `python script.py`
cozy-tui run --debug script.py   # ...with App(debug=True) on, no code change needed
python examples/<name>/<name>.py   # run an example
```

The CLI lives in `cozy_tui/cli.py` (argparse; the `cozy-tui` console script and
`python -m cozy_tui` both call `cli.main`). The demo moved out of `__main__.py`
into `cozy_tui/demo.py`; `__main__.py` is now a thin dispatcher. `__version__`
is exposed from `cozy_tui/__init__.py` (via `importlib.metadata`, `"dev"` when
running from an uninstalled source tree). `cozy-tui run` (`cli._cmd_run`) executes
the target file via `runpy.run_path(..., run_name="__main__")` with its own
directory prepended to `sys.path` and the remaining CLI args forwarded as
`sys.argv[1:]`, matching `python script.py`; `--debug` just sets `COZY_TUI_DEBUG=1`
before running it.

There is no linter/formatter config, but the code is `black`/`isort`-formatted (note the `# fmt: off` blocks in `events.py`).

Clipboard tests self-skip when no platform backend is available (see `tests/test_clipboard.py`); CI runs them under Xvfb/sway to exercise the X11/Wayland backends for real.

## Architecture

`cozy_tui` is a from-scratch TUI library. The only third-party dependency is `rich` (used to render `Markdown`/`MarkdownInput` and to syntax-highlight `TracebackView`/`crash_screen.show_traceback`); everything else — input parsing, clipboard, unicode width — is hand-rolled on the standard library. Targets Python 3.10+.

### Render loop (`app.py`)
`App.run()` is the single event loop. Each frame:
1. `render()` clears an in-memory cell `buffer` (a `rows × cols` grid of `Cell`), applies docks, then calls `widget.draw(self)` on every widget, then overlays.
2. Widgets paint by calling `app.write(x, y, text, style)` — the canvas is the `App` itself.
3. A **double buffer** (`_prev_cells`) enables diff rendering: `_do_diff_render()` emits VT escapes only for changed cells; `_do_full_render()` repaints everything (forced via `invalidate()` after screen switches / resize). Call `invalidate()` whenever you change something the diff can't detect.

Between frames the loop blocks in `wait_input()` (never busy-spins) and wakes for input, the cursor blink (`BLINK_INTERVAL`), terminal resize, `tick_interval`/animation frames, or worker results.

`App(catch_errors=True)` (the default) wraps the loop in `except Exception`: the terminal is restored exactly as on a clean exit (same `finally`), then `crash_screen.show_traceback(exc)` runs as a *separate* full-screen crash view — deferred until after the `finally` so it never starts before this app's raw mode/alt screen/mouse tracking is fully torn down. `KeyboardInterrupt`/`EOFError` are handled first and never reach the crash screen. Pass `catch_errors=False` for a script/test that wants `run()` to raise normally instead (or that has no real terminal for the crash screen to block on). `show_traceback`'s own internal `App` always sets `catch_errors=False` — otherwise a crash *in* the crash screen would recurse into showing a crash screen for itself, without end.

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

### Debugging (`App(debug=True)`, `_debug_pane.py`)
`app.debug(*values, sep=" ")` is a `print()`-equivalent that's safe to call while the raw-mode/alt-screen loop is running (a bare `print()` would corrupt the display) — it appends to a bounded ring buffer (`_debug_log`, `deque(maxlen=500)`) instead. It's a no-op, and the buffer isn't even allocated, unless the app was built with `debug=True`; `debug=None` (the constructor default) resolves from `COZY_TUI_DEBUG=1`, which `cozy-tui run --debug script.py` sets — an explicit `True`/`False` always wins over the env var. `debug_log_path=` additionally tails each line to a file. `default_logs=True` (the default, only meaningful when `debug=True`) has `App` log its own focus changes, key presses, and mouse clicks/drags via `app.debug()` automatically — mouse-move/hover is deliberately excluded (fires far too often to be useful). **F12** toggles a Chrome-DevTools-style panel docked to the top-left corner at a quarter of the screen (`self.cols // 2` x `self.rows // 2`, `center=False`) showing the log live; `_debug_pane.py`'s `DebugPane` is a `Box` (title "Debug Log") wrapping a self-updating `ScrollView` subclass that only rebuilds its rows when `App._debug_seq` has moved since its last draw. `app.toggle_debug_pane()` is the public method (F12 just binds to it) for triggering it from your own menu item/button/key binding.

### Input parsing (`events.py`) & platform backend (`_console.py`)
`events.py` parses raw VT byte sequences into `Key.*` constants, `MouseClick`/`MouseDrag`, and bracketed-`Paste` events — this is the portable core. `_console.py` isolates the *only* platform-specific parts: entering raw+VT mode and blocking for input. Windows uses the Console API (`ctypes`/`kernel32`); POSIX uses `termios`/`tty`/`select`. Keep platform-specific code confined to `_console.py`.

### Unicode width (`_width.py`)
A built-in `wcwidth`-style layer: `char_width(ch)` returns 0 (combining/ZWJ — dropped by `write`), 1, or 2 (CJK/emoji — the trailing cell is blanked to stay grid-aligned). This keeps the cell grid honest without a `wcwidth` dependency.

### Background work
`app.run_worker(func, on_result=, on_error=)` runs `func` on a daemon thread; results are queued and the callbacks fire on the **main thread** from the event loop (never touch the UI from a worker thread directly).

### Clipboard (`clipboard.py`)
Built-in, no `pyperclip`. Picks a native backend per platform (Win32 API, `pbcopy`/`pbpaste`, `wl-clipboard`/`xclip`/`xsel`) with an OSC 52 fallback. `clipboard.backend()` reports the chosen one.

### Rich bridging (`_rich_bridge.py`)
Shared by every widget that borrows Rich's rendering instead of reimplementing it (`Markdown`, `TracebackView`): `to_cozy_style(rich_style, base)` converts a resolved `rich.style.Style` into a `cozy_tui.style.Style`, mapping colors down to the 16 named ANSI colors (via `cozy_color()`) regardless of Rich's original color space — `ansi.py`'s own depth-aware downgrading takes it from there. Widgets render through a headless `rich.console.Console` (`console.render_lines(...)`), never printing Rich's own ANSI output to stdout, so it composes with the raw-mode/alt-screen renderer instead of corrupting it. `TracebackView` (`widgets/display/traceback_view.py`) applies this to `rich.traceback.Traceback`; `crash_screen.show_traceback(exc)` wraps it into a ready-made full-screen crash view (Esc quits, C copies via `clipboard.copy`).
