# Examples

The `examples/` directory contains runnable apps. Each example adds the project root to `sys.path` automatically, so they can be run from any directory.

### `examples/basic/basic.py` — Hello World

Minimal app with a label and a quit button. Good starting point.

```bash
python examples/basic/basic.py
```

### `examples/timer_app/timer.py` — Timer / Forms

Demonstrates `Input`, `Button`, `Checkbox`, `ProgressBar`, `Dropdown`, `ListView`, `VBox`, `HBox`, and `Grid` in a single app.

```bash
python examples/timer_app/timer.py
```

### `examples/dock_layout/dock_layout.py` — Dock Layout

Demonstrates `App.dock()` with a header (`top`), status bar (`bottom`), sidebar (`left`), and a `fill` main area that claims the remaining space. Resize the terminal to watch the layout re-flow.

```bash
python examples/dock_layout/dock_layout.py
```

### `examples/overlay/overlay.py` — Overlays / Modals

A base screen with a button that opens a centered, dimmed modal dialog. Tab is confined to the dialog; Esc or a click outside dismisses it.

```bash
python examples/overlay/overlay.py
```

### `examples/command_palette/command_palette.py` — Command Palette

A Spotlight/VS Code-style fuzzy command launcher in a modal overlay: a custom widget with its own text buffer and filtered result list. Press `p` to open, type to fuzzy-search, Enter/click to run. Includes a background-worker command that keeps the UI responsive.

```bash
python examples/command_palette/command_palette.py
```

### `examples/kanban/kanban.py` — Kanban Board

A keyboard-driven To Do / Doing / Done board built from Boxes + ListViews. Tab switches columns, Up/Down selects, ←/→ moves a card between columns, `a`/`d` add/delete, `?` shows a help overlay, `c` opens a confirm-clear modal.

```bash
python examples/kanban/kanban.py
```

### `examples/snake/snake.py` — Snake

A real-time Snake game: a fully custom drawing widget painting the field cell-by-cell, driven by `app.tick_interval` (game logic decoupled from render rate), with a "Game Over" modal offering Restart / Quit.

```bash
python examples/snake/snake.py
```

### `examples/calculator_app/calculator.py` — Calculator

A fully keyboard-driven calculator supporting `+`, `-`, `×`, `÷`, `**` (exponent), `√` (square root), and `!` (factorial).

```bash
python examples/calculator_app/calculator.py
```

**Calculator keyboard shortcuts:**

| Key | Action |
|---|---|
| `0`–`9`, `.` | Enter digits |
| `+` `-` `*` `/` | Arithmetic operators (`*` inserts `×`, `/` inserts `÷`) |
| `^` | Exponent (`**`) |
| `r` | Square root (`√(`) |
| `!` | Factorial |
| Enter / `=` | Evaluate |
| Backspace | Delete last character |
| `c` | Clear |
| ESC | Quit |

### `examples/markdown_editor/markdown_editor.py` — Markdown Editor

A live Markdown editor built on `MarkdownInput`: type on the left, press **Tab** to render the Rich Markdown preview, and click **Edit** to return.

```bash
python examples/markdown_editor/markdown_editor.py
```

### `examples/todo_app/todo.py` — Todo List

A persistent todo list using `CheckList` and `Input`; items are saved to `todo_data.json` next to the script and reloaded on start.

```bash
python examples/todo_app/todo.py
```
