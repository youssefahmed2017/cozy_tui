# Examples

The `examples/` directory contains runnable apps. Each example adds the project root to `sys.path` automatically, so they can be run from any directory.

### `examples/dashboard/dashboard.py` — Dashboard (multi-widget showcase)

A mock download manager that wires several widgets into one app: **`Tabs`** organise Downloads / Activity / About panels; a **`ProgressBar`** per file is advanced by an `app.every` timer; a **`Spinner`** spins next to *Start* while work is in flight; the Activity panel is an autoscrolling **`ScrollView`** log; and **`app.toast`** pops as each file — and the whole batch — completes.

```bash
python examples/dashboard/dashboard.py
```

### `examples/basic/basic.py` — Hello World

Minimal app with a label and a quit button. Good starting point.

```bash
python examples/basic/basic.py
```

### `examples/deploy/deploy.py` — Deploy Console (State + Log + overlays)

A release console that puts the three features together the way they actually show up together. Three `State` objects are the whole model: `service` alone drives the panel's border title, the header label, and every future log line, and nothing in the file updates a widget by hand. A **`Log`** with `markup=True` streams the deploy output, coloring the level tag inside each line while the message stays plain. **Overlays** guard the irreversible parts — deploying opens a hand-built modal `Box` (raw `open_overlay`, so you can see what the ready-made dialogs are made of), rollback uses `app.confirm()`, and rename uses `app.prompt()` and writes back into the state explicitly, since binding is one-way.

Two details worth reading for: `emit()` *reads* `service.value` instead of binding to it, so renaming later doesn't rewrite history; and both markup edge cases are on screen — a registry path containing `[a-f0-9]+` renders literally, while a username that genuinely looks like a tag goes through `markup.escape()`.

```bash
python examples/deploy/deploy.py
```

### `examples/screens/screens.py` — Cozy Arcade (screens)

Four screens — menu, settings, game, over — where the whole of the navigation is `app.show(...)`. It exists to show the two things screens give you that rebuilding a UI on every switch would not: **widgets keep their state** (start a round, duck into settings mid-game, come back — score, clock, typed name and focused widget are all where you left them), and **`on_show`/`on_hide` are where the rest of the state goes** (the game screen cancels its tick timer on the way out and restarts it on the way in, so wandering off pauses the round instead of letting it run out unwatched).

Also worth reading for: the "over" screen is built once and *refilled* before each show rather than rebuilt, and the first screen created adopts the app so no initial `app.show()` is needed.

```bash
python examples/screens/screens.py
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
