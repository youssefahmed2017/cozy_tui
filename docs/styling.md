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

A freshly constructed `App()` with no explicit `style=` picks up the active theme's `style`. Already-built widgets are **not** retroactively affected by a later theme switch — colors are resolved at construction/draw time, like the rest of this library's styling; `selection_style()` is the exception, since it's re-read from the active theme on every draw.

### Switching themes interactively

**Ctrl+T** opens a searchable theme palette by default on every `App` — type to filter `Theme.MODES` by substring, Up/Down/Home/End to move, Enter or a click to pick, Esc/click-outside to cancel:

```python
app.open_theme_palette()   # what Ctrl+T calls; trigger it yourself from a menu item or button
```

For a plain one-shot-per-press cycle instead of a searchable list, `app.cycle_theme()` advances to the next built-in mode (wrapping) — it isn't bound to a key by default, so bind it yourself if you want that instead of the palette.

Since widgets don't retroactively pick up a later theme switch on their own, an app that wants its own colors (not just the shared `selection_style()` highlight) to follow a switch needs to either share `style=app.style` with its containers (so mutating `app.style` cascades automatically) or poll `get_theme().mode` for changes and re-apply. See `cozy_tui/demo.py` for a worked example of both.

---
