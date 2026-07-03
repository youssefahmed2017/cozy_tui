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
