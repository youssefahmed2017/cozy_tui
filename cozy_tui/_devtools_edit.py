"""Internal: the Elements tab's **live editing** support -- synthesizing an
editable constructor-style snippet from a live widget, and applying an edited
one back onto it.

The snippet is *not* the widget's real source. Nothing here reads the file the
widget was constructed in; the text is rebuilt from the widget's current
attributes every time the selection changes, so it always describes what the
widget **is right now** rather than what it was written as. Applying an edit
sets those attributes on the live object, and the next frame draws the result
-- the same "assign an attribute, the diff renderer notices" path every other
widget mutation in this library takes.

**Values are parsed structurally, never evaluated.** ``ast.parse(mode="eval")``
checks the shape (one call, keyword arguments only) and ``ast.literal_eval``
handles each value, so an edited snippet can only ever supply plain literals --
never call a function, read an attribute, or run arbitrary code. This mirrors
TermQuarium's Cheat Console parser (examples/aquarium/termquarium/console.py),
for the same reason: a devtool that takes typed input should not be an eval
prompt, even one pointed at your own process.

``Style(...)`` is the single exception to "literals only", and it is
special-cased structurally rather than looked up: its own arguments must
themselves be literals. Colors are the thing most worth poking at live, and
requiring a pre-built Style object would have made the most interesting field
in the panel read-only.
"""

from __future__ import annotations

import ast
from typing import Any

from cozy_tui.style import Style


class EditError(Exception):
    """A user-facing problem with an edited snippet. The message is shown as-is
    in the Elements tab -- never a raw traceback."""


#: Position first, then content-ish attributes, in the order they're listed.
#: A field appears in the snippet only if the widget actually has it *and* its
#: current value is a plain literal, so the same table serves every widget
#: without a per-class registry: a `Label` shows `text`, a `Box` also shows
#: `title`/`width`/`height`, a `Checkbox` also shows `checked`.
_POSITION = ("x", "y")
_FIELDS = (
    "text",
    "title",
    "link",
    "value",
    "placeholder",
    "checked",
    "progress",
    "width",
    "height",
    "align",
    "gap",
)

#: Everything the snippet may assign. Anything else is rejected by name rather
#: than silently setattr'd -- a typo'd `txt=` that quietly created a new unused
#: attribute and appeared to do nothing would be worse than an error.
EDITABLE = frozenset(_POSITION + _FIELDS + ("style",))

_LITERAL_TYPES = (str, int, float, bool)


# ── building the snippet ─────────────────────────────────────────────────────


def snippet_fields(widget) -> list[tuple[str, Any]]:
    """The ``(name, value)`` pairs shown for ``widget``, in display order."""
    fields: list[tuple[str, Any]] = []
    for name in _POSITION + _FIELDS:
        if not hasattr(widget, name):
            continue
        value = getattr(widget, name)
        if isinstance(value, _LITERAL_TYPES) or value is None:
            fields.append((name, value))
    return fields


def _style_snippet(style: Style) -> str:
    # raw_bg, not bg: Style's constructor re-applies the internal "_bg" suffix
    # to named colors, so echoing the stored value back would round-trip into
    # "red_bg_bg" the moment an unedited snippet was applied.
    styles = list(style.styles)
    return f"Style(fg={style.fg!r}, bg={style.raw_bg!r}, styles={styles!r})"


def build_snippet(widget) -> str:
    """Render ``widget``'s current state as an editable constructor snippet."""
    lines = [f"{type(widget).__name__}("]
    for name, value in snippet_fields(widget):
        lines.append(f"    {name}={value!r},")
    style = getattr(widget, "style", None)
    if isinstance(style, Style):
        lines.append(f"    style={_style_snippet(style)},")
    lines.append(")")
    return "\n".join(lines)


# ── parsing an edited snippet ────────────────────────────────────────────────


def _literal(label: str, node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        raise EditError(f"{label}: only plain literal values are allowed") from None


def _style_from_call(node: ast.Call) -> Style:
    if node.args:
        raise EditError("Style(...) takes keyword arguments only")
    kwargs: dict[str, Any] = {}
    for keyword in node.keywords:
        if keyword.arg is None:
            raise EditError("Style(**...) isn't supported")
        if keyword.arg not in ("fg", "bg", "styles"):
            raise EditError(f"Style has no {keyword.arg!r} argument")
        kwargs[keyword.arg] = _literal(f"style.{keyword.arg}", keyword.value)
    try:
        return Style(**kwargs)
    except Exception as exc:  # e.g. styles=5 -- Style itself rejects it
        raise EditError(f"Style(...): {exc}") from None


def _value(label: str, node: ast.AST) -> Any:
    if isinstance(node, ast.Call):
        # The one callable form allowed, matched structurally by name -- no
        # lookup of `Style` (or anything else) in any namespace happens here.
        if isinstance(node.func, ast.Name) and node.func.id == "Style":
            return _style_from_call(node)
        raise EditError(f"{label}: only Style(...) may be called")
    return _literal(label, node)


def parse_snippet(text: str) -> dict[str, Any]:
    """Parse an edited snippet into ``{field: value}``. Raises :class:`EditError`
    with a message meant to be read by a human in the panel."""
    text = text.strip()
    if not text:
        raise EditError("nothing to apply")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise EditError(f"syntax error: {exc.msg}") from None
    call = tree.body
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
        raise EditError("expected Widget(field=value, ...)")
    if call.args:
        raise EditError("positional arguments aren't supported -- use field=value")
    values: dict[str, Any] = {}
    for keyword in call.keywords:
        if keyword.arg is None:
            raise EditError("**kwargs isn't supported")
        values[keyword.arg] = _value(keyword.arg, keyword.value)
    return values


# ── applying it ──────────────────────────────────────────────────────────────


def _kind(value: Any) -> str | None:
    """A coarse type bucket, used to reject an edit that would break the widget
    (``x='wide'``) while still allowing the harmless widening (``x=2`` → ``2.5``)
    and any assignment where one side is None."""
    if value is None:
        return None
    if isinstance(value, bool):  # before int -- bool *is* an int
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "text"
    return type(value).__name__


def _same(current: Any, new: Any) -> bool:
    if isinstance(current, Style) and isinstance(new, Style):
        # Style has no __eq__, so identity would report every apply as a change.
        return (current.fg, current.bg, current.styles) == (new.fg, new.bg, new.styles)
    try:
        return bool(current == new)
    except Exception:
        return False


def apply_snippet(widget, text: str) -> list[str]:
    """Apply an edited snippet to ``widget``. Returns the names of the fields
    that actually changed (empty if the snippet matched the widget already).

    Every field is validated **before** anything is assigned, so a mistake in
    the last line can't leave the widget half-updated -- which, on a live UI
    you're looking at, would be indistinguishable from the edit having worked.
    """
    values = parse_snippet(text)
    pending: list[tuple[str, Any]] = []
    for key, new in values.items():
        if key not in EDITABLE:
            raise EditError(f"{key!r} isn't editable here")
        if not hasattr(widget, key):
            raise EditError(f"{type(widget).__name__} has no {key!r}")
        current = getattr(widget, key)
        current_kind, new_kind = _kind(current), _kind(new)
        if current_kind and new_kind and current_kind != new_kind:
            raise EditError(f"{key} expects {current_kind}, got {new_kind}")
        if not _same(current, new):
            pending.append((key, new))
    changed = []
    for key, new in pending:
        try:
            setattr(widget, key, new)
        except Exception as exc:  # a property setter that rejects the value
            raise EditError(f"{key}: {exc}") from None
        changed.append(key)
    return changed
