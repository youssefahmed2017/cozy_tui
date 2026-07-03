# Input & Interaction

## Key Bindings

### Global (handled by App)

| Key | Action |
|-----|--------|
| Tab | Focus next widget |
| Shift+Tab | Focus previous widget |
| Ctrl+C | Exit the app |
| Scroll Up / Page Up / Ctrl+Up | Scroll content up |
| Scroll Down / Page Down / Ctrl+Down | Scroll content down |

### Input widget

| Key | Action |
|-----|--------|
| Arrow keys | Move cursor |
| Home / End | Jump to line start / end |
| Backspace | Delete character behind cursor |
| Delete | Delete character ahead of cursor |
| Enter / Shift+Enter | Insert newline (multiline mode only) |
| UP / DOWN | Move between lines (multiline mode only) |

### Button widget

| Key | Action |
|-----|--------|
| Enter | Activate button |
| Space | Activate button |

### Checkbox widget

| Key | Action |
|-----|--------|
| Enter | Toggle checked state |
| Space | Toggle checked state |

### Registering custom global shortcuts

```python
app.on_key(Key.ESC, lambda: "quit")      # return "quit" to exit
app.on_key(Key.ENTER, submit_form)        # any function works too
```

Available key constants in `cozy_tui.events.Key`:

`ESC`, `ENTER`, `BACKSPACE`, `TAB`, `SHIFT_TAB`, `SHIFT_ENTER`,
`UP`, `DOWN`, `LEFT`, `RIGHT`, `HOME`, `END`,
`DELETE`, `INSERT`, `PAGE_UP`, `PAGE_DOWN`,
`CTRL_UP`, `CTRL_DOWN`, `CTRL_LEFT`, `CTRL_RIGHT`, `CTRL_C`,
`F1`–`F12`

**Modifier combos.** Terminals only send Alt/Ctrl combined with another key, so use the helpers:

```python
from cozy_tui.events import Key

app.on_key(Key.alt("s"), save)          # Alt+S   → "alt+s"
app.on_key(Key.ctrl("f"), find)         # Ctrl+F  → the raw control byte "\x06"
app.on_key(Key.F5, refresh)             # F5
app.on_key(Key.ctrl(Key.F5), hard_refresh)  # Ctrl+F5 → "ctrl+F5"

# Key.ALT == "alt" and Key.CTRL == "ctrl" are the underlying prefixes.
```

- `Key.alt(c)` → `"alt+" + c` (matches `read_key()` for `Alt+<char>`, e.g. `Key.alt("backspace")`).
- `Key.ctrl(c)` → the actual control byte for a **letter** (`Key.ctrl("a") == Key.CTRL_A`), or a `"ctrl+<key>"` string otherwise (e.g. an F-key).
- `Key.shift(c)` → `"shift+" + c` (used for F-keys).
- **Modified F-keys** parse to canonical `"ctrl+F5"`, `"shift+F5"`, `"ctrl+shift+F12"` … The modifier order is always `ctrl`, `alt`, `shift`, and the helpers compose in that order — `Key.ctrl(Key.shift(Key.F5)) == "ctrl+shift+F5"`.

---

## Mouse Support

Mouse clicks are handled automatically:

- **Click any focusable widget** → gives it focus
- **Click a Button** → gives it focus and activates it
- **Click a Checkbox** → gives it focus and toggles it
- **Scroll wheel** → scrolls the app content up/down

No extra setup needed — mouse support is enabled automatically when `app.run()` starts.

---

## Focus System

Focus determines which widget receives keyboard input. Only `focusable` widgets (`Input`, `Button`, `Checkbox`, `ListView`, `Dropdown`, `Table`, `Collapsible`, `Tree`) can hold focus. A **focusable container defers to its children**: Tab dives into a `Box`'s first focusable child instead of stopping on the box. A `Box` is not a Tab stop on its own unless you construct it with `Box(..., focusable=True)`, which is useful for empty or decorative boxes you still want selectable.

```python
app.focus(widget)      # set initial focus manually
```

While running:
- **Tab** moves focus to the next focusable widget
- **Shift+Tab** moves focus to the previous one
- **Mouse click** focuses the clicked widget

Focused widgets receive a visual highlight — inputs show a white background and a blinking cursor; buttons invert their colors and go bold. The parent `Box` also highlights its border when any child has focus.

---

## Scrolling

When content is taller than the terminal, the app scrolls vertically. Scroll controls:

| Key / Action | Effect |
|---|---|
| Scroll wheel up | Scroll up 3 rows |
| Scroll wheel down | Scroll down 3 rows |
| Page Up / Ctrl+Up | Scroll up 3 rows |
| Page Down / Ctrl+Down | Scroll down 3 rows |

---
