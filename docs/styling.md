# Styling

Styles are created with the `Style` class:

```python
Style(fg="color", bg="color", styles=["bold", "dim", "underline"])
```

**Available colors:**

The 16 named colors:

`black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`,
`bright_black`, `bright_red`, `bright_green`, `bright_yellow`,
`bright_blue`, `bright_magenta`, `bright_cyan`, `bright_white`

Both `fg` and `bg` also accept the following non-named forms (any mix is fine):

| Form              | Example              | Meaning                                    |
| ----------------- | -------------------- | ------------------------------------------ |
| `"rgb(R,G,B)"`    | `"rgb(255,120,0)"`   | 24-bit truecolor, components `0`–`255`     |
| `"#rrggbb"`       | `"#ff7800"`          | 24-bit truecolor from a hex string         |
| `"#rgb"`          | `"#f70"`             | shorthand hex (`#f70` → `#ff7700`)         |
| `"color(N)"`      | `"color(200)"`       | 256-color palette index, `N` = `0`–`255`   |

Truecolor and 256-color require a terminal that supports them (most modern
terminals do); named colors work everywhere.

**Color depth.** cozy_tui picks a depth from the environment at import
(`NO_COLOR` → no color; `COLORTERM=truecolor`/`24bit` → truecolor;
`TERM=*256color*` → 256; otherwise truecolor). Override it at runtime:

```python
from cozy_tui import set_color_depth, get_color_depth

set_color_depth("256")   # "none" | "16" | "256" | "truecolor"
```

At `"16"`/`"256"`, hex/rgb and (for `"16"`) `color(N)` values are automatically
snapped to the nearest color the depth can represent; at `"none"` color is
suppressed but text styles (bold, underline, …) still apply. The
[`NO_COLOR` convention](https://no-color.org) is honored automatically.

**Text styles:** `"bold"`, `"dim"`, `"italic"`, `"underline"`, `"blink"`

**Example:**

```python
Style(fg="white", bg="blue")                            # white text on blue background
Style(fg="bright_white", bg="black", styles=["bold"])   # bold bright white on black
Style(fg="cyan")                                        # cyan text, default background
Style(fg="#ffcc00", bg="#102030")                       # hex truecolor fg on dark bg
Style(fg="rgb(255,120,0)")                              # orange truecolor text
Style(fg="color(200)", styles=["italic"])               # 256-palette pink, italic
```

---

## Inline markup

A whole widget shares one `Style`. When you need colors *within* a line, opt into markup:

```python
from cozy_tui.widgets import Label

Label(2, 1, "[bold red]Error[/] connecting to [cyan]db-01[/]", markup=True)
```

`markup=True` is supported by **`Label`**, **`Text`**, **`AnimatedLabel`**, and **`Log`**. It is off by default everywhere, so text that already contains brackets can't change meaning when you upgrade.

A tag names any combination of the attributes and colors `Style` already understands — there is no separate markup color table:

```
[red]   [bold]   [bold red]   [dim italic bright_black]
[#ff8800]   [rgb(255,136,0)]   [color(33)]
[on blue]   [white on red]
```

`[/]` closes the most recent tag; `[/red]` does the same and reads better when tags are nested. Tags nest and inherit the enclosing style, and an unclosed tag simply runs to the end of the string.

### Unrecognized tags are left alone

The parser only consumes a bracket group when *every* word inside it is a real style or color. Everything else renders as itself:

```python
Label(2, 1, "[INFO] items[0] matched [a-z]+", markup=True)
# ...draws exactly that
```

This is what makes `markup=True` safe on a `Log`, whose lines usually come from somewhere other than the person who enabled it. When you *do* need a literal bracket that would otherwise parse, escape it:

```python
from cozy_tui.markup import escape

log.log(f"user said: {escape(untrusted)}")   # or write "\\[red]" by hand
```

### Working with markup directly

`cozy_tui.markup` is a small public module if you want to render tags yourself:

| Function | Description |
|----------|-------------|
| `render(markup, base=None)` | Parse into `(text, Style)` runs, each resolved against `base` |
| `plain(markup)` | The text with every tag stripped — what it measures and wraps as |
| `escape(text)` | Backslash-escape `[` so `text` survives unchanged |
| `write_runs(canvas, x, y, runs)` | Paint runs left to right; returns the width written |

---

## Themes

A `Theme` is a named bundle of colors the library's shared visual language draws from — the base `App` style, an `accent` color for emphasis, `success`/`warning`/`error`/`info` colors (what `app.toast(...)` picks its color from), a `muted` color for secondary text, and the `selection_fg`/`selection_bg` pair the focused-row highlight is built from. That highlight — `selection_style()` — is shared by `ListView`, `RadioSet`, `CheckList`, `Table`, `Tree`, `Dropdown`, `Checkbox`, `RightClickMenu`, `Slider`, and `MenuBar`, so switching themes re-colors every one of those widgets at once.

```python
from cozy_tui import Theme, get_theme, set_theme

Theme.MODES   # every built-in preset name, e.g. "default", "monochromatic",
              # "ocean", "forest", "cyberpunk", ... (over 20 and growing)

theme = Theme(mode="ocean")            # from a built-in preset (case-insensitive)
theme = Theme(style=Style(fg="white", bg="#1a1a2e"))  # custom base, default preset for the rest
theme = Theme(mode="ocean", accent="bright_green")     # override one role, keep the rest of the preset
```

A theme does nothing on its own until it's made active:

```python
theme.activate()          # or: set_theme(theme)
get_theme()                # the process-wide active theme (Theme(), i.e. "default", until something activates one)
```

A freshly constructed `App()` with no explicit `style=` picks up the active theme's `style`.

**Switching is live.** `set_theme(...)` re-colors a running app: the canvas takes the new theme's background and foreground and forces a full repaint, and everything resolved at draw time follows with it — `selection_style()` (every list/table/tree/menu highlight), the modal scrim, `Toast` colors, `Bindings`, the dialogs' accent.

What *doesn't* change is a color you chose explicitly. An `App(style=Style(...))` or a `Widget(style=Style(...))` keeps exactly what it was given — a theme switch has no business discarding a deliberate choice.

The app's base `Style` object is mutated in place rather than replaced, which is worth knowing: any widget you built with `style=app.style` holds that same object and therefore re-colors for free.

```python
panel = Box(0, 0, "400x200", title="Files", style=app.style)   # follows theme switches
fixed = Box(0, 0, "400x200", title="Files", style=Style(fg="red"))  # stays red
```

To react yourself — re-deriving a color you computed once, say — subscribe:

```python
from cozy_tui.theme import on_theme_change, unsubscribe_theme

on_theme_change(lambda theme: setattr(label, "style", Style(fg=theme.accent)), owner=self)
```

`owner=` makes the subscription weak, so a discarded object stops being called (and stops being kept alive) automatically. Passing `owner`'s own bound method works correctly too.

### Switching themes interactively

**Ctrl+T** opens a searchable theme palette by default on every `App` — type to filter `Theme.MODES` by substring, Up/Down/Home/End to move, Enter or a click to pick, Esc/click-outside to cancel:

```python
app.open_theme_palette()   # what Ctrl+T calls; trigger it yourself from a menu item or button
```

For a plain one-shot-per-press cycle instead of a searchable list, `app.cycle_theme()` advances to the next built-in mode (wrapping) — it isn't bound to a key by default, so bind it yourself if you want that instead of the palette.

Either way the running app re-colors immediately — no restart, and no manual `invalidate()`. Widgets holding their own explicit `Style(...)` keep it; pass `style=app.style` (or subscribe via `on_theme_change`) for anything you want to follow along. See `cozy_tui/demo.py` for a worked example.

---
