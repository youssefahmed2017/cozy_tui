# Testing

`cozy_tui.testing.Harness` drives an app headlessly — no terminal, no event loop, no `sleep`.

```python
from cozy_tui import App
from cozy_tui.testing import Harness
from cozy_tui.widgets import Button, Label

def test_clicking_saves():
    app = App(full=False, size="600x200")
    status = Label(0, 2, "Ready")
    button = Button(0, 0, "Save")
    button.on_click(lambda _b: setattr(status, "text", "Saved!"))
    app.add(button)
    app.add(status)

    with Harness(app) as ui:
        ui.click(button)
        assert "Saved!" in ui
```

Build your app exactly as you normally would, hand it to a `Harness`, and drive it. Events go through the same `App` routing `run()` uses, so focus, modals, key bindings, and mouse capture all behave as they do for a real user.

Every action re-composes the screen, so an assertion right after one sees what a user would see. Actions chain: `ui.focus(field).type("ab").press(Key.BACKSPACE)`.

---

## Setup

```python
Harness(app, *, size=None)
```

The harness forces `app.full = False` — a full-screen app would otherwise size its buffer from the real terminal (or fall back to 80×24 when there isn't one), making assertions depend on the machine running the test. Pass `size="400x100"` (virtual pixels, as everywhere else) to fix the screen size explicitly.

It also sets `catch_errors = False`. The default turns an exception into a full-screen crash view, which in a test means a hang on a terminal that isn't there — and a green run for broken code. With the harness, exceptions propagate to your test.

Used as a context manager it marks the app as quit on exit; that's optional.

---

## Reading the screen

| Member | Description |
|---|---|
| `ui.screen` | The whole screen as one string, trailing blanks stripped |
| `ui.lines` | Every row as a list of strings |
| `ui.line(row)` | One row as a string |
| `"text" in ui` | Shorthand for `"text" in ui.screen` |
| `ui.find("text")` | `(col, row)` of the first occurrence, or `None` |
| `ui.cell(col, row)` | The raw `Cell` — for asserting on **color and style**, which `screen` throws away |
| `ui.compose()` | Re-run the draw pass; call after mutating a widget by hand |

```python
assert ui.line(0) == "Hello"
assert ui.cell(0, 0).style.fg == "red"
assert ui.find("Error") is None
```

> **Composing, not rendering.** The harness fills the cell buffer via `App._compose()` and never writes to the terminal, so your test output stays clean instead of being interleaved with thousands of escape sequences. The trade-off: the diff renderer isn't exercised — this harness tests *your app*, not cozy_tui's renderer.

---

## Keyboard

| Method | Description |
|---|---|
| `ui.press(*keys)` | Send `Key.*` constants or single characters |
| `ui.type(text)` | Type character by character, as a person would |
| `ui.paste(text)` | Deliver the text as one bracketed-paste event |

`type` and `paste` are genuinely different: `type("abc")` fires per-character validation, `on_change`, and undo coalescing three times; `paste("abc")` fires them once.

```python
ui.focus(field).type("hello")
ui.press(Key.TAB, Key.ENTER)
```

---

## Mouse

| Method | Description |
|---|---|
| `ui.click(target, button=0)` | Click a widget (its top-left cell) or a `(col, row)` point |
| `ui.right_click(target)` | Button 2 — context menus |
| `ui.double_click(target)` | Two clicks inside the double-click window |
| `ui.hover(target)` | Motion with no button — fires enter/leave/hover |
| `ui.drag(target)` / `ui.release(target)` | Motion with a button held, then release |
| `ui.scroll(target, down=True, amount=1)` | Wheel scroll |

`target` is a widget or an explicit `(col, row)` tuple. Clicking a widget moves focus exactly as a real click does.

```python
ui.click(field).drag((5, 0))       # select the first five characters
assert field._sel_text() == "hello"
```

---

## Time

`ui.advance(seconds)` moves a virtual clock forward and fires whatever `app.after` / `app.every` timers that crosses. **Nothing sleeps** — a 30-second timeout is testable instantly, and the offset accumulates across calls.

```python
app.after(30, lambda: setattr(status, "text", "timed out"))

ui.advance(29)
assert "timed out" not in ui
ui.advance(2)
assert "timed out" in ui
```

---

## Background work

`app.run_worker` uses a real thread, so `ui.settle(timeout=2.0)` really does wait — but only until results arrive, and never past the timeout. Callbacks fire on the calling thread, the same guarantee the event loop gives.

```python
app.run_worker(fetch_data, on_result=show_data)
ui.settle()
assert "42 rows" in ui
```

---

## Other

| Member | Description |
|---|---|
| `ui.focused` | The focused widget |
| `ui.focus(widget)` | Focus a widget |
| `ui.cursor` | `(col, row)` of the terminal cursor, or `None` when hidden |
| `ui.resize("300x100")` | Resize the screen; docked and flex layouts reflow |
| `ui.quit_requested` | `True` once something called `app.quit()` |

```python
def test_narrow_terminal_still_shows_the_footer():
    ui.resize("300x100")
    assert "Ctrl+Q" in ui.lines[-1]
```
