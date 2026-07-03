# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

`cozy_tui` is a cross-platform Python TUI library. It renders terminal UIs by maintaining an in-memory cell grid, serializing changed cells to ANSI escape sequences, and writing them to stdout in one shot per frame. Raw input and terminal setup are abstracted in `cozy_tui/_console.py`, which picks a backend at import: Windows Console API (`ctypes.windll.kernel32`) or POSIX `termios`/`tty` + `select`. There is no ncurses dependency.

Dependencies: `rich` (required; used by `Markdown`/`MarkdownInput`). The clipboard is built in (`cozy_tui/clipboard.py`, cross-platform), so there is **no `pyperclip`** dependency. Python 3.10+ required. Packaged via `pyproject.toml` (`pip install -e .`, `[dev]` extra for pytest); ships a `py.typed` marker. Tests live in `tests/` (`python -m pytest`).

## Running examples

```bash
python examples/basic/basic.py
python examples/timer_app/timer.py
python examples/calculator_app/calculator.py
```

Each example adds the project root to `sys.path`, so no install step is needed.

## Architecture

### Rendering pipeline

1. `App.render()` calls `clear()` to reset the cell buffer, then calls `widget.draw(canvas)` on every top-level widget.
2. `canvas.write(x, y, text, style)` writes into `App.buffer` — a 2-D list of `Cell(char, style)`. It is Unicode-width-aware (`cozy_tui/_width.py`): a wide glyph (CJK/emoji) fills its cell and blanks the next as a continuation cell (`char = ""`, emits nothing so the terminal's 2-column advance stays aligned); a zero-width char (combining mark, ZWJ, BOM) is dropped. `text_width()` gives display width; `Label.natural_width` uses it.
3. On the first frame (or after resize/`invalidate()`), `_do_full_render()` serializes every row. On subsequent frames, `_do_diff_render()` emits only the cells that differ from `_prev_cells`.
4. Cursor positioning is handled separately via `_cursor_esc()`, which emits an ANSI sequence to place the real terminal cursor at the focused widget's computed screen position.

### Coordinate system

- All widget positions are in **terminal characters** (columns × rows), not pixels.
- Widgets inside a `Box` use coordinates **relative to the box interior** (inside the border). Absolute positions are resolved by walking `widget.parent` chains via `abs_x` / `abs_y` properties.
- `Box` sizes accept a `"WxH"` string in "virtual pixels" divided by 30 (e.g., `"900x600"` = 30 cols × 20 rows). `App` uses `SCALE = 10` for its own size string; widgets inside boxes use the box's implicit scale of 30.

### Widget base class (`cozy_tui/widget.py`)

All widgets inherit from `Widget`. Key contract:
- `focusable = False` by default; override to `True` for interactive widgets.
- `draw(canvas)` — must be implemented; writes to the canvas.
- `on_key(key)` — receives key events when the widget has focus.
- `contains(col, row)` — hit-testing for mouse events.
- `natural_width(scale)` / `natural_height(scale)` — used by layout containers.

### Widget package layout (`cozy_tui/widgets/`)

Widgets are grouped into four subpackages, but all are re-exported flat from the top-level `cozy_tui` package (import as `from cozy_tui import Button`, not from the subpackage):
- `display/` — `Label`, `AnimatedLabel`/`GlowAnimation`, `Markdown`, `Text`, `ProgressBar`
- `input/` — `Input`, `MarkdownInput`
- `layout/` — `Box`, `Collapsible`, `Layout`, `VBox`, `HBox`, `Grid`
- `selection/` — `Button`, `Checkbox`, `CheckList`/`CheckItem`, `Dropdown`, `ListView`/`ListItem`, `Table`/`TableRow`, `Tree`/`TreeNode`

`cozy_tui/__init__.py` is the canonical list of public widgets and their source files.

### Input widget composition

`Input` (`widgets/input/input.py`) is split into mixins across sibling files, combined via `class Input(_HistoryMixin, _DrawMixin, _KeysMixin, Widget)`:
- `_input_draw.py` — `_DrawMixin`: renders characters, handles scroll offset, selection highlight, masked mode
- `_input_keys.py` — `_KeysMixin`: keyboard dispatch (arrows, home/end, ctrl+word, delete, etc.)
- `_input_history.py` — `_HistoryMixin`: undo/redo stacks
- `_input_clipboard.py` — `_clipboard_get`/`_clipboard_set` helper functions (not a mixin) that delegate to the built-in `cozy_tui.clipboard` (see below)

`MarkdownInput` subclasses `Input` and overrides `draw()` to render Rich Markdown when unfocused.

### Clipboard (`cozy_tui/clipboard.py`)

A small, purpose-built clipboard — `copy(text)` / `paste() -> str` / `available()` / `backend()` — deliberately *not* a full pyperclip replacement. A backend is picked once at import (`_select_backend`): Win32 API via ctypes on Windows, `pbcopy`/`pbpaste` on macOS, `wl-copy`/`wl-paste` → `xclip` → `xsel` on Linux, else an OSC 52 escape for copy with no paste. Both `copy` and `paste` are best-effort: they swallow errors, `paste` returns `""` when unavailable, `available()` reports whether a full round-trip backend exists (used to gate the round-trip test), and `backend()` returns the selected backend's name (`"win32"`/`"pbcopy"`/`"wl-clipboard"`/`"xclip"`/`"xsel"`/`"osc52"`) — CI asserts on it to prove each Linux backend is actually exercised (X11 tools under Xvfb, `wl-clipboard` under headless sway). Input widgets reach it only through `_input_clipboard.py`.

### `CheckList` / `CheckItem` (`cozy_tui/widgets/selection/check_list.py`)

A scrollable list where every item has an independent checked state — combines `ListView` navigation with `Checkbox` toggling.

**`CheckItem(text, value=None, checked=False)`** — the item type. `value` defaults to `text` when omitted.

**Key API:**
- `append(item)`, `insert(index, item)`, `remove(item)`, `clear()` — mutate the list (accept raw strings or `CheckItem`).
- `set_checked(value, checked)` — flip one item by value.
- `check_all()`, `uncheck_all()`, `toggle_all()` — bulk state operations; do **not** fire `on_toggle`.
- `checked_values` — list of `.value` for all checked items.
- `checked_items` — list of `CheckItem` objects for all checked items (use when `.text` is also needed).
- `selected` / `selected_index` — value/index of the highlighted row.
- `on_change(func)` — `func(value)` fires when the cursor moves to a different row.
- `on_toggle(func)` — `func(value, checked)` fires when an item is toggled by the user (Enter, Space, or click); not called by bulk methods.

**Behaviour:** Up/Down/Home/End moves the cursor. Enter or Space toggles the highlighted item. A mouse click moves the cursor to the clicked row and toggles it immediately.

### Layout containers (`Layout`, `VBox`, `HBox`, `Grid`)

Layout subclasses override `_arrange()` to set `child.x`, `child.y`, and `self._computed_width` / `self._computed_height`. The `draw()` method re-dirties `_dirty = True` each frame so sizes recompute if content changes. Children passed to a layout should use `(0, 0)` for position — the layout overrides them.

### Dock layout (`cozy_tui/_dock.py`)

`App.dock(widget, side, margin=0)` and `Box.dock(widget, side, margin=0)` register a widget to an edge — `side` is `"left"`, `"right"`, `"top"`, `"bottom"`, or `"fill"`. Both delegate to the single shared function `dock_layout(items, x, y, w, h, scale)`, differing only in the starting rectangle: `App` passes the whole screen `(0, 0, cols, rows)`; `Box` passes its interior `(1, 1, inner_w, inner_h)`.

The algorithm consumes a **shrinking rectangle** in dock order: each `top`/`bottom` dock eats a horizontal band (the widget stretches across the remaining width); each `left`/`right` eats a vertical band (stretches across the remaining height); `"fill"` claims the entire leftover. So **order matters** — the last non-fill dock sees the smallest rect, and a sidebar docked after a header+footer only spans the band between them.

Stretching works via `Widget.dock_resize(w, h, scale)`, a hook called with the assigned cell slice. The base is a no-op (fixed-size widgets like `Label` just anchor at the slice's top-left); **`Box` overrides it** to grow into the slice (`self.width = (w-2)*scale`, minus 2 for the border). Docks are re-resolved every frame — `App._apply_docks()` runs at the top of `render()`, `Box._apply_docks()` at the start of `draw()` — so layouts re-flow on terminal resize. Note `App` applies `scroll_y` to all output, so docked widgets are not scroll-fixed on non-`full` apps. Demo: `examples/dock_layout/dock_layout.py`.

### Overlays / z-layer (`App.open_overlay` / `close_overlay`)

Overlays draw above the base widgets on a separate stack (`self._overlays`, last == topmost) — the basis for dialogs/menus/tooltips. `render()` draws base widgets, then `_draw_overlays()`. Overlays are **screen-fixed**: `_draw_overlays` flips `self._scroll_active = False` so `write()` skips the `scroll_y` offset (and doesn't grow `_content_rows`) while they draw. A `dim` overlay first calls `_apply_backdrop()` (greys every drawn cell via a shared `_backdrop_style`, chars kept); a `center` overlay is re-centred each frame from its `natural_width/height` (so it's a per-frame layout like docks, surviving resize). A **modal** overlay confines input: `_collect_focusables()` returns only the topmost modal's focusables (Tab cycles inside it), and in `run()` a modal intercepts all keys (Esc closes if `close_on_escape`, no global handlers/scroll) and mouse clicks (outside the widget's `contains()` are swallowed, or dismiss if `close_on_click_outside`). Hit-testing was refactored into `_hit_widget(root, col, row)` reused by both base `_hit_test` and the modal path. Opening a modal moves focus to its first child and stores the prior focus in the `_Overlay` record; closing restores it and fires `on_close`. `_cursor_esc` uses scroll 0 under a modal so a focused overlay Input's cursor lands correctly. Non-modal overlays are visual only. Demo: `examples/overlay/overlay.py`. `App.prompt(title, initial, on_submit, on_cancel, ...)` is a convenience built on this: it opens a `PromptDialog` (`widgets/input/prompt.py`, a self-contained bordered one-line text widget) as a centered dimmed modal, wiring Enter→`on_submit(text)`+close and Esc/click-outside→`on_cancel` (a `submitted` flag prevents `on_cancel` firing after a submit). **`Dropdown` is a real consumer**: its popup `ListView` is pushed via `open_overlay(modal=True, dim=False, close_on_click_outside=True)` and positioned (not centered) one row below the header in screen coords, so it floats above siblings; the widget grabs its `App` reference from the `canvas` in `draw()` (stored as `self._app`) to open the overlay from `on_key`/`on_mouse_click`, and the `ListView`'s `on_select` (Enter or row click) confirms and closes.

### Focus traversal (`App._collect_focusables` / `_focusables_in`)

Tab order is a preorder walk, but a **focusable container defers to its focusable descendants**: `_focusables_in(widget)` recurses into `children` first and, if any descendant is focusable, returns those instead of the container — so Tab dives into a `Box`'s first child rather than stopping on the box. A container is only its own stop when it has no focusable descendant *and* is itself focusable. `Box` is **non-focusable by default** (`Box(..., focusable=True)` opts in), so empty/decorative boxes stay out of the cycle while boxes wrapping fields still dive into their content. Containers that manage their own internal navigation (`Collapsible`) opt out by exposing `children` as `[]`; `Tree`/`Table` simply have no `children` attribute, so they're single stops. Mouse clicks route through `_first_focusable()` so clicking a container dives the same way Tab does. `Box._has_focused()` returns true for self-focus *or* descendant focus, so the border highlights in both cases.

### Event loop (`App.run`)

- Enters raw+VT mode via `_console.enable_raw()` (Windows `SetConsoleMode`, or POSIX `tty.setraw`); restored on exit. Enter/exit escape strings (alt screen, mouse, bracketed paste) are plain ANSI and portable.
- The idle loop is **event-driven, not busy-poll**: instead of `time.sleep`, it calls `_console.wait_input(timeout)` (`WaitForSingleObject` / `select`) that blocks until input or the next scheduled wake (blink/tick), capped at `_IDLE_POLL = 0.1s` so resize and worker results are still noticed.
- `kbhit()` (in `events.py`) checks the internal `_buf` first, then delegates to `_console.kbhit()`.
- `read_key()` parses VT sequences from `os.read(0, 1024)` bulk reads to reliably disambiguate ESC from CSI sequences.
- Mouse events are parsed as SGR (`ESC [ < … M/m`) or X10 (`ESC [ M …`) sequences; `MouseClick` and `MouseDrag` objects are dispatched by `_hit_test()`.
- **Background work**: `App.run_worker(func, *, on_result, on_error)` runs `func` on a daemon thread and queues its result to `_worker_results`; the loop's `_drain_workers()` fires the callback on the main thread and re-renders, so worker callbacks never touch the UI off-thread.

### `Style` and `Cell`

`Style(fg, bg, styles)` stores named ANSI colors (e.g., `"blue"`, `"bright_white"`). The `bg` value is stored internally with a `_bg` suffix so `ansi.py`'s lookup tables can distinguish fg from bg. `style_esc()` in `ansi.py` is permanently cached by `(fg, bg, styles_tuple)`.
