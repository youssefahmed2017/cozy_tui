# Examples

The `examples/` directory contains runnable apps. Each example adds the project root to `sys.path` automatically, so they can be run from any directory.

### `examples/basic/basic.py` — Hello World

Minimal app with a label and a quit button. Good starting point.

```bash
python examples/basic/basic.py
```

### `examples/file_manager/file_manager.py` — cozy-files (file manager)

A mouse-and-keyboard TUI file manager and the broadest showcase in the repo: a custom widget draws a header breadcrumb, a scrolling directory listing (icons, sizes, dates, hover highlight), and a status bar. **Right-click** anywhere for a context menu with icons, shortcut hints, disabled items and a `New ▸ File/Folder` submenu — Open, Copy path (to the system clipboard), Copy/Cut/Paste, Rename…, Delete. Rename/new use `app.prompt`; deletes use a confirm modal; directory loads and copy/move/delete run on background `run_worker` threads. Deletes are confirmed and a paste never overwrites (it auto-renames). Pass a start directory as an argument.

```bash
python examples/file_manager/file_manager.py          # start in the current directory
python examples/file_manager/file_manager.py ~/projects
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

### `examples/toasts/toasts.py` — Toasts & Spinner

Buttons that raise info / success / warning / error **toasts** (they stack in the corner and auto-dismiss on a timer), plus a "Load data" button that shows a **`Spinner`** while a background `run_worker` runs and fires a success toast when it finishes — the idiomatic async-feedback loop. Built on the App's `after` / `every` timers.

```bash
python examples/toasts/toasts.py
```

### `examples/drop_area/drop_area.py` — Drop Files Area

A `DropFilesArea` that files whatever you drag onto the terminal (or paste the path of) into a `dropped/` folder next to the script. Demonstrates that a terminal delivers a drag-and-drop as the file's *path text* (a bracketed paste), which the widget resolves on the local filesystem and copies — never overwriting. A path dropped over SSH surfaces as a friendly "not found here".

```bash
python examples/drop_area/drop_area.py
```

### `examples/tabs/tabs.py` — Tabbed Container

A `Tabs` widget with Files / Settings / About panels. Focus lands on the tab strip (←/→ or Home/End to switch, click a title), and Tab dives into the active panel's controls. Only the active panel is drawn and focusable.

```bash
python examples/tabs/tabs.py
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

### `examples/game_2048/game_2048.py` — 2048

The classic slide-and-merge puzzle. A custom widget paints a colored tile grid with truecolor styling (that auto-downgrades on 16/256-color terminals); arrow keys / WASD / hjkl slide, a mouse **drag** swipes, and a modal overlay handles the win / game-over screens. The game logic is pure and unit-tested (`tests/test_game_2048.py`).

```bash
python examples/game_2048/game_2048.py
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
