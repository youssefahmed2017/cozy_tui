# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

`cozy_tui` is a Windows-only Python TUI library. It renders terminal UIs by maintaining an in-memory cell grid, serializing changed cells to ANSI escape sequences, and writing them to stdout in one shot per frame. It uses `msvcrt` / Windows Console API (`ctypes.windll.kernel32`) for raw input; there is no ncurses dependency.

Dependencies: `cozy-kit`, `pyperclip`, and optionally `rich` (for `MarkdownInput`). Python 3.10+ required.

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
2. `canvas.write(x, y, text, style)` writes into `App.buffer` — a 2-D list of `Cell(char, style)`.
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

### Input widget composition

`Input` is split across four files to keep it manageable:
- `widgets/input.py` — main class, position/cursor/selection logic
- `widgets/_input_draw.py` — `_DrawMixin`: renders characters, handles scroll offset, selection highlight, masked mode
- `widgets/_input_keys.py` — `_KeysMixin`: keyboard dispatch (arrows, home/end, ctrl+word, delete, etc.)
- `widgets/_input_history.py` — `_HistoryMixin`: undo/redo stacks

`MarkdownInput` subclasses `Input` and overrides `draw()` to render Rich Markdown when unfocused.

### `CheckList` / `CheckItem` (`cozy_tui/widgets/check_list.py`)

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

### Event loop (`App.run`)

- Switches the Windows console to raw+VT mode via `SetConsoleMode`.
- Polls `kbhit()` (uses `WaitForSingleObject` on stdin, not `msvcrt.kbhit`, to catch mouse scroll events in ConPTY).
- `read_key()` parses VT sequences from `os.read(0, 1024)` bulk reads to reliably disambiguate ESC from CSI sequences.
- Mouse events are parsed as SGR (`ESC [ < … M/m`) or X10 (`ESC [ M …`) sequences; `MouseClick` and `MouseDrag` objects are dispatched by `_hit_test()`.

### `Style` and `Cell`

`Style(fg, bg, styles)` stores named ANSI colors (e.g., `"blue"`, `"bright_white"`). The `bg` value is stored internally with a `_bg` suffix so `ansi.py`'s lookup tables can distinguish fg from bg. `style_esc()` in `ansi.py` is permanently cached by `(fg, bg, styles_tuple)`.
