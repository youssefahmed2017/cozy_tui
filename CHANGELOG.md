# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Inline markup** — `markup=True` on `Label`, `Text`, `AnimatedLabel`, and the
  new `Log` interprets style tags inside the text. Tags name the same
  attributes and colors `Style` already understands, so there is no separate
  markup color table. See [docs/styling.md](docs/styling.md#inline-markup).

  ```python
  Label(2, 1, "[bold red]Error[/] connecting to [cyan]db-01[/]", markup=True)
  ```

  An unrecognized bracket group is left as literal text rather than raising or
  vanishing, so `"[INFO] items[0]"` still reads correctly with markup on;
  `markup.escape()` (or a backslash) forces a literal bracket that *would* have
  parsed. `cozy_tui.markup` exposes `render`/`plain`/`escape`/`write_runs` for
  rendering tags yourself.

- **`Log` widget** — an append-only, auto-scrolling text log. A `ScrollView`
  that manages its own rows, bounded by `max_lines` (default 1000) so a
  long-running app's memory stays flat.

  ```python
  log = Log(2, 2, "600x160", markup=True)
  log.log("Server started")
  log.log("[red]connection refused[/] — retrying")
  ```

- **Screens** — `app.screen(name)` gets or creates a named set of top-level
  widgets; `app.show(name)` switches to it. No subclass to write and no routing
  table: `screen.add`/`dock`/`focus` are the App calls you already make.
  See [docs/concepts.md](docs/concepts.md#screens).

  ```python
  menu = app.screen("menu"); menu.add(title_label)
  game = app.screen("game"); game.add(board)
  app.show("menu")
  ```

  Screens **keep their widgets** — switching away and back leaves a half-typed
  form, a scroll position, and the focused widget as they were. The first
  screen created adopts whatever the app already had, so screens can be added
  to an existing app without reordering its setup. `screen.on_show(f)` /
  `screen.on_hide(f)` fire on each switch. An app that never calls `screen()`
  is unaffected.

  `screen.on_key(key, f)` registers a binding that applies only while that
  screen shows and **wins over** the app-wide binding for the same key — so Esc
  can mean "back" on one screen and "quit" on another with no dispatcher in the
  middle checking `current_screen`.

- **`examples/screens/`** — a four-screen arcade shell demonstrating both
  state preservation across switches and `on_show`/`on_hide` pausing a timer.

- **`Button(height=N)`** — a button can now be more than one row tall. It paints
  a solid block in its own style with the label on the middle row, and is
  clickable on every row.

  ```python
  Button(0, 0, "7", width=8, height=3)   # a key you aim at, not a line of text
  ```

- **`ListView.selected_index` / `CheckList.selected_index` are settable** —
  the public way to restore the cursor after rebuilding a list (clamped, and a
  no-op on an empty list). Previously this meant reaching for `_index`.

- **`Tabs.remove_tab(index_or_title)`** — returns the removed panel, or `None`.
  The selection stays on the tab you were looking at wherever possible.

- **Widget lifecycle** — the operations for changing a UI after it's built.
  See [docs/concepts.md](docs/concepts.md#widget-lifecycle).

  - **`app.remove(widget)`** — remove a widget from anywhere in the tree. It
    moves focus off whatever it takes away, which a bare
    `container.children.remove(...)` cannot: a removed widget that keeps
    `app.focused` still receives every keystroke while being invisible, and
    presents as a UI that silently stopped responding. `Widget.remove(child)`
    and `Widget.clear()` are the bare container versions.
  - **`Widget.visible`** — `False` skips the widget in drawing, hit-testing,
    and the Tab order (subtree and all), and collapses it out of a `VBox` /
    `HBox` along with its surrounding `gap`.
  - **`Widget.disabled`** — `True` dims the widget and makes it inert: not
    focusable, not clickable, and it swallows a click rather than letting it
    fall through to whatever is behind it. Dimming is automatic — `widget.style`
    returns a dimmed copy — so it applies to every widget in the library.
  - **`Widget.on_focus(f)` / `Widget.on_blur(f)`** — focus lifecycle callbacks.
    `on_blur` is where field validation belongs: it fires once the user is done
    with the field rather than on every keystroke.

  ```python
  submit.disabled = not form_is_valid()
  advanced.visible = show_advanced
  email.on_blur(lambda w: mark_invalid(w) if not valid(w.value) else None)
  app.remove(old_card)
  ```

- **`examples/deploy/`** — a release console using `State`, `Log`, and overlays
  together. Replaces `examples/reactive/`, `examples/logs/`, and
  `examples/overlay/`, which each demonstrated one of the three in isolation.

- **`Key.SPACE`** — an alias for `" "`. Space was always bindable as a plain
  character; the constant exists so looking for it beside `Key.ENTER` finds
  something.

### Changed

- **Examples brought up to date.** `todo_app` and `timer_app` used a hand-rolled
  `switch_screen()` that assigned `app.widgets`, `app.focused`, and
  `app._key_handlers` directly and rebuilt every screen from scratch on each
  switch; both now use `Screen`, keep what you typed, and show validation
  errors via a hidden `Label` rather than by rebuilding the form. `calculator`
  registers keys through `app.on_key` instead of poking `_key_handlers`, and its
  keypad uses 3-row-tall buttons. `dashboard`'s Activity panel is now a `Log`
  with markup instead of a hand-fed `ScrollView` of `Label`s.

## [0.5.0] - 2026-07-22

Reactive state, a public test harness, a syntax-highlighting `Code` widget, and
live widget editing in DevTools — plus three `Input` fixes, one of which had
been quietly corrupting typed text.

### ⚠ Breaking

- **`Widget.__init__(..., name=...)` and `Widget.name` are gone.** Use
  `type(widget).__name__`, which is what every internal consumer now does.
  A subclass passing `name=` up to `Widget`/`Layout` raises `TypeError`:

  ```python
  # before
  super().__init__(x, y, style, name="Fish")
  # after
  super().__init__(x, y, style)
  ```

- **`Widget.__str__` removed** (along with `MarkdownInput.__str__` and
  `CodeInput.__str__`). `str(widget)` now returns the default object repr;
  format `type(widget).__name__` instead.
- **`Layout.__init__(..., name=...)` removed** — it existed only to forward a
  name to `Widget`.

### Added

- **Reactive state** — `State` is an observable value; pass one where a widget
  property is expected and the widget follows every change. `Widget.bind(attr,
  value)` is the integration point, and holds the widget weakly so a discarded
  widget drops its own subscription. Reactive today: `Label`/`Button`/
  `Checkbox.text`, `Hyperlink.text`/`link`, `Box.text`/`title`, `Text.text`,
  `ProgressBar.progress`, `Code.code`. Explicit by design — a plain `str` is
  never reactive, and binding is one-way. See
  [docs/concepts.md](docs/concepts.md#reactive-state-cozy_tuistate).

  ```python
  title = State("Downloads")
  app.add(Label(2, 1, title))
  app.add(Box(2, 3, "400x100", title=title))
  title.value = "Downloads (3)"   # both update
  ```

- **`Code` widget** — syntax-highlighted source via Rich's `Syntax` (Pygments),
  bridged into the cell grid. Self-sizing, cached, and lenient about an
  unrecognized `lang` (renders unhighlighted rather than raising). Position is
  keyword-only so the source reads first.

  ```python
  Code('print("hello world")', lang="python")
  ```

- **`CodeInput` widget** — an editable code field that renders highlighted when
  unfocused and as plain text with a cursor while being typed in, mirroring
  `MarkdownInput`.
- **`cozy_tui.testing.Harness`** — drive an app headlessly: `ui.click(button)`,
  `ui.type("hello")`, `assert "Saved!" in ui`. Virtual time (`ui.advance(30)`
  fires a 30-second timer instantly, and carries wall-clock animations with
  it), `ui.settle()` for background workers, and no escape sequences written to
  your test output. See [docs/testing.md](docs/testing.md).
- **Live editing in DevTools** — the Elements tab renders the selected widget
  as an editable snippet; edit a value, press Apply, and the running UI updates.
  Values are parsed structurally (`ast.literal_eval`), never evaluated, so an
  edit can only ever supply plain literals.
- **Full cursor-shape support** — `ansi.CURSOR_SHAPES`, `cursor_shape_esc()`,
  and `TERMINAL_CURSOR_STYLES`, covering all six DECSCUSR shapes.
- **`ProgressBar.progress`** — a settable property matching the constructor
  argument (previously only `get()`/`set()`).
- **`examples/reactive/`** — a download manager driven entirely by `State`.
- **`on_theme_change(callback, owner=)` / `unsubscribe_theme(callback)`** — react
  to a theme switch yourself. `owner=` makes the subscription weak.

### Changed

- **`Input.flash` now reaches the terminal.** It selects the blinking or steady
  DECSCUSR shape, so the terminal blinks the cursor at the rate the user
  configured instead of the app toggling visibility on a 0.5s timer. Previously
  only the steady shapes were ever emitted and `flash` had no effect on a
  `vertical`/`block` cursor.
- **`cursor_style="underline"` is now drawn by the terminal.** It previously
  hid the real cursor and painted a fake underlined cell into the buffer, which
  also forced a full re-render twice a second.
- **Theme switching is now live.** `set_theme(...)` re-colors a running app
  instead of only affecting what's built afterwards: the canvas takes the new
  theme's colors and forces a full repaint, and anything resolved at draw time
  (`selection_style()`, the modal scrim, `Toast`, `Bindings`, the dialogs'
  accent) follows. An explicit `App(style=...)` / `Widget(style=...)` is never
  overridden. The app's base `Style` is mutated in place, so widgets built with
  `style=app.style` re-color for free.
- **Ctrl+C inside a modal** now goes through the normal handler chain, so a
  registered `on_key(Key.CTRL_C, ...)` runs instead of the app quitting
  unconditionally.

### Fixed

- **`Input.on_change` never fired.** The handler slot existed and was
  documented, but no edit path ever invoked it — so `input.on_change(state.set)`
  silently did nothing. Typing, backspace, paste, and undo/redo all fire it now;
  navigation and programmatic assignment deliberately do not.
- **Clicking into an `Input` and typing deleted the first character.** A click
  left a live selection anchor "for potential drag"; typing moves the cursor
  away from it, so the app treated the typed text as selected and the next
  keystroke replaced it. The anchor is now established only when a drag actually
  begins.
- **`State.subscribe(self.method, owner=self)` leaked its owner.** A bound
  method holds its instance strongly, so the weak `owner` reference could never
  die; that case is now stored as a `weakref.WeakMethod`.
- **A bracketed paste skipped `Input`'s bookkeeping** — it returned early from
  `on_key`, so a pasted value never marked the field as touched (and so never
  triggered validation display).

## [0.4.2] and earlier

See the [commit history](https://github.com/youssefahmed2017/cozy_tui/commits/master).
