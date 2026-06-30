import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Box, Button, HBox, Label, Style, VBox
from cozy_tui.events import Key

# ── app ───────────────────────────────────────────────────────────────────────

app = App(full=True, size=None, style=Style(fg="white", bg="black"))

# ── state ─────────────────────────────────────────────────────────────────────

_expr = ""  # expression being built
_just_evaluated = False  # True right after = was pressed

# ── layout ───────────────────────────────────────────────────────────────────
# 4 buttons × 8 wide + 3 gaps × 1 = 35 wide button area
# Box inner width = 37, total = 39 cols, box starts at x=2 → ends at col 41

box = Box(
    2,
    1,
    "1110x570",
    border="rounded",
    style=Style(fg="cyan", bg="black"),
    title=" CALCULATOR ",
)

lbl_expr = Label(2, 2, " ", style=Style(fg="bright_black"))
lbl_result = Label(2, 3, "0", style=Style(fg="bright_green", styles=["bold"]))
lbl_sep = Label(1, 4, "─" * 35, style=Style(fg="cyan"))

box.add(lbl_expr)
box.add(lbl_result)
box.add(lbl_sep)

# ── math ─────────────────────────────────────────────────────────────────────

_NS = {"__builtins__": {}, "sqrt": math.sqrt, "factorial": math.factorial}


def _eval(e: str) -> str:
    e = e.replace("×", "*").replace("÷", "/")
    e = e.replace("√", "sqrt")  # √(9) → sqrt(9)
    e = re.sub(r"(\d+)!", r"factorial(\1)", e)
    open_p = e.count("(") - e.count(")")
    if open_p > 0:
        e += ")" * open_p  # auto-close e.g. √(9  →  sqrt(9)
    result = eval(e, _NS)
    if isinstance(result, int):
        return str(result)
    if isinstance(result, float):
        if result.is_integer() and abs(result) < 1e15:
            return str(int(result))
        return f"{result:.10g}"
    return str(result)


# ── actions ───────────────────────────────────────────────────────────────────


def push(text: str) -> None:
    global _expr, _just_evaluated
    if _just_evaluated:
        # After a result: digits start fresh; operators continue from result
        if text not in "+-×÷**!":
            _expr = ""
        _just_evaluated = False
    _expr += text
    lbl_expr.text = _expr


def do_equals() -> None:
    global _expr, _just_evaluated
    if not _expr:
        return
    try:
        val = _eval(_expr)
        lbl_result.text = val
        _expr = val
        _just_evaluated = True
        lbl_expr.text = ""
    except Exception:
        lbl_result.text = "Error"
        _just_evaluated = False


def do_clear() -> None:
    global _expr, _just_evaluated
    _expr = ""
    _just_evaluated = False
    lbl_expr.text = ""
    lbl_result.text = "0"


def do_back() -> None:
    global _expr, _just_evaluated
    _just_evaluated = False
    _expr = _expr[:-1]
    lbl_expr.text = _expr
    if not _expr:
        lbl_result.text = "0"


# ── button factory ────────────────────────────────────────────────────────────

_DIGIT_S = Style(fg="white", bg="blue")
_OP_S = Style(fg="white", bg="magenta")
_CTRL_S = Style(fg="white", bg="bright_black")
_EQ_S = Style(fg="black", bg="bright_green", styles=["bold"])

BTN_W = 8  # enforced minimum by Button._width()


def _btn(label: str, action, style=None) -> Button:
    b = Button(0, 0, label, width=BTN_W, style=style or _DIGIT_S)
    if callable(action):
        b.on_click(lambda _, a=action: a())
    else:
        b.on_click(lambda _, t=action: push(t))
    return b


def _row(*specs) -> HBox:
    """Build one horizontal button row from (label, action[, style]) tuples."""
    row = HBox(0, 0, gap=1)
    for label, action, *rest in specs:
        row.add(_btn(label, action, rest[0] if rest else None))
    return row


# ── button grid ───────────────────────────────────────────────────────────────

vbox = VBox(1, 5, gap=1)

vbox.add(
    _row(
        ("C", do_clear, _CTRL_S),
        ("⌫", do_back, _CTRL_S),
        ("√(", "√(", _OP_S),
        ("!", "!", _OP_S),
    )
)
vbox.add(
    _row(
        ("7", "7"),
        ("8", "8"),
        ("9", "9"),
        ("÷", "÷", _OP_S),
    )
)
vbox.add(
    _row(
        ("4", "4"),
        ("5", "5"),
        ("6", "6"),
        ("×", "×", _OP_S),
    )
)
vbox.add(
    _row(
        ("1", "1"),
        ("2", "2"),
        ("3", "3"),
        ("-", "-", _OP_S),
    )
)
vbox.add(
    _row(
        ("0", "0"),
        (".", "."),
        ("**", "**", _OP_S),
        ("+", "+", _OP_S),
    )
)

box.add(vbox)

btn_eq = Button(1, 15, "=", width=35, style=_EQ_S)
btn_eq.on_click(lambda _: do_equals())
box.add(btn_eq)

app.widgets = [box]

# ── keyboard ──────────────────────────────────────────────────────────────────

for _d in "0123456789.":
    app._key_handlers[_d] = (lambda d: lambda: push(d))(_d)

app._key_handlers.update(
    {
        "+": lambda: push("+"),
        "-": lambda: push("-"),
        "*": lambda: push("×"),
        "/": lambda: push("÷"),
        "!": lambda: push("!"),
        "^": lambda: push("**"),
        "r": lambda: push("√("),
        "(": lambda: push("("),
        ")": lambda: push(")"),
        "=": lambda: do_equals(),
        Key.ENTER: lambda: do_equals(),
        Key.BACKSPACE: lambda: do_back(),
        "c": lambda: do_clear(),
        "C": lambda: do_clear(),
        Key.ESC: lambda: "quit",
    }
)

app.run()
