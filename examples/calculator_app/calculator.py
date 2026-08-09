import ast
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, State, Style
from cozy_tui.events import Key
from cozy_tui.widgets import Box, Button, HBox, Label, Rule, VBox

# ── app ───────────────────────────────────────────────────────────────────────

app = App(full=True, size=None, style=Style(fg="white", bg="black"), title="CALCULATOR")

# ── state ─────────────────────────────────────────────────────────────────────
# The two display lines are States. The actions below only ever set these; the
# Labels are bound to them (see the layout section) and repaint themselves, so
# there's no `label.text = ...` plumbing threaded through every handler.

expr_text = State("")  # the small grey expression line
result_text = State("0")  # the big green result line

_expr = ""  # expression being built (logic, distinct from what's displayed)
_just_evaluated = False  # True right after = was pressed

# ── layout ───────────────────────────────────────────────────────────────────
# 4 buttons × 8 wide + 3 gaps × 1 = 35 wide button area
# Box inner width = 37, total = 39 cols, box starts at x=2 → ends at col 41
#
# Buttons are BTN_H rows tall (see the button factory): a calculator key is a
# *slab* you aim at, not a line of text, so the extra rows are both nicer to
# look at and a much bigger mouse target. That sets the box height: 4 header
# rows, then 5 key rows of (3 + 1 gap), then the wide "=" — 29 interior rows.

box = Box(
    2,
    1,
    "390x290",
    border="rounded",
    style=Style(fg="cyan", bg="black"),
    title=" CALCULATOR ",
)

lbl_expr = Label(2, 2, expr_text, style=Style(fg="bright_black"))
lbl_result = Label(2, 3, result_text, style=Style(fg="bright_green", styles=["bold"]))
lbl_sep = Rule(1, 4, style=Style(fg="cyan"))  # auto-fills the box interior

box.add(lbl_expr)
box.add(lbl_result)
box.add(lbl_sep)

# ── math ─────────────────────────────────────────────────────────────────────

_NS = {"__builtins__": {}, "sqrt": math.sqrt, "factorial": math.factorial}

# eval() below runs on the app's single render-loop thread -- a chain like
# "9**9**9" (9 ^ 387420489) is valid Python and would have eval() itself
# compute a result hundreds of millions of digits long, freezing the whole
# UI. _pow_result_bits sizes up every ** in the expression *before* eval()
# ever runs, entirely in cheap floating-point math, so a result this
# explosive is rejected instead of actually being computed.
_MAX_POW_RESULT_BITS = 100_000  # ~30,000 decimal digits -- generous for any
# real calculation, far short of anything that would visibly stall.


class _ResultTooLarge(Exception):
    pass


def _pow_result_bits(node) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        v = abs(node.value)
        return math.log2(v) if v > 1 else 0.0
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return _pow_result_bits(node.operand)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
        base_bits = _pow_result_bits(node.left)
        if isinstance(node.right, ast.Constant) and isinstance(
            node.right.value, (int, float)
        ):
            exponent = abs(node.right.value)
        else:
            # The exponent is itself a Pow chain -- 2**bits recovers its
            # (equally estimated) magnitude without ever computing it.
            exponent = 2 ** _pow_result_bits(node.right)
        bits = base_bits * exponent
        if bits > _MAX_POW_RESULT_BITS:
            raise _ResultTooLarge()
        return bits
    if isinstance(node, ast.BinOp):
        return max(_pow_result_bits(node.left), _pow_result_bits(node.right))
    return 0.0  # calls (sqrt/factorial), names, etc. -- not a ** chain


def _eval(e: str) -> str:
    e = e.replace("×", "*").replace("÷", "/")
    e = e.replace("√", "sqrt")  # √(9) → sqrt(9)
    e = re.sub(r"(\d+)!", r"factorial(\1)", e)
    open_p = e.count("(") - e.count(")")
    if open_p > 0:
        e += ")" * open_p  # auto-close e.g. √(9  →  sqrt(9)
    try:
        tree = ast.parse(e, mode="eval")
    except SyntaxError:
        tree = None  # eval() below will raise & report its own "Error"
    if tree is not None:
        try:
            _pow_result_bits(tree.body)
        except _ResultTooLarge:
            raise OverflowError("result too large to compute")
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
    expr_text.set(_expr)


def do_equals() -> None:
    global _expr, _just_evaluated
    if not _expr:
        return
    try:
        val = _eval(_expr)
        result_text.set(val)
        _expr = val
        _just_evaluated = True
        expr_text.set("")
    except Exception:
        result_text.set("Error")
        _just_evaluated = False


def do_clear() -> None:
    global _expr, _just_evaluated
    _expr = ""
    _just_evaluated = False
    expr_text.set("")
    result_text.set("0")


def do_back() -> None:
    global _expr, _just_evaluated
    _just_evaluated = False
    _expr = _expr[:-1]
    expr_text.set(_expr)
    if not _expr:
        result_text.set("0")


# ── button factory ────────────────────────────────────────────────────────────

_DIGIT_S = Style(fg="white", bg="blue")
_OP_S = Style(fg="white", bg="magenta")
_CTRL_S = Style(fg="white", bg="bright_black")
_EQ_S = Style(fg="black", bg="bright_green", styles=["bold"])

BTN_W = 8  # enforced minimum by Button._width()
BTN_H = 3  # rows per key — the label lands on the middle one


def _btn(label: str, action, style=None) -> Button:
    b = Button(0, 0, label, width=BTN_W, height=BTN_H, style=style or _DIGIT_S)
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

btn_eq = Button(1, 25, "=", width=35, height=BTN_H, style=_EQ_S)
btn_eq.on_click(lambda _: do_equals())
box.add(btn_eq)

app.add(box)

# ── keyboard ──────────────────────────────────────────────────────────────────
# Registered through app.on_key so each binding can carry a description, which
# is what a Bindings("auto") legend and the Ctrl+P command palette read.

for _key, _token in {
    **{d: d for d in "0123456789."},
    "+": "+",
    "-": "-",
    "*": "×",
    "/": "÷",
    "!": "!",
    "^": "**",
    "r": "√(",
    "(": "(",
    ")": ")",
}.items():
    app.on_key(_key, (lambda t: lambda: push(t))(_token))

app.on_key("=", do_equals, description="Evaluate", section="Calculator")
app.on_key(Key.ENTER, do_equals)
app.on_key(Key.BACKSPACE, do_back, description="Delete last", section="Calculator")
app.on_key("c", do_clear, description="Clear", section="Calculator")
app.on_key("C", do_clear)
app.on_key(Key.ESC, app.quit, description="Quit", section="Calculator")

if __name__ == "__main__":
    app.run()
