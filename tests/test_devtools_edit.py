"""Live editing in the DevTools Elements tab: the snippet synthesizer/parser
(cozy_tui/_devtools_edit.py) and its wiring into the panel."""

import pytest

from cozy_tui import Style
from cozy_tui._devtools_edit import (
    EditError,
    apply_snippet,
    build_snippet,
    parse_snippet,
)
from cozy_tui.events import Key
from cozy_tui.widgets import Box, Checkbox, Label, ProgressBar

from tests.test_devtools import make_ui

# ── building the snippet ─────────────────────────────────────────────────────


def test_snippet_describes_the_widgets_current_state():
    snippet = build_snippet(Label(3, 2, "Hello"))
    assert snippet.startswith("Label(")
    assert "x=3," in snippet
    assert "y=2," in snippet
    assert "text='Hello'," in snippet
    assert snippet.endswith(")")


def test_snippet_only_lists_fields_the_widget_actually_has():
    assert "checked=" not in build_snippet(Label(0, 0, "hi"))
    assert "checked=False," in build_snippet(Checkbox(0, 0, "opt"))
    assert "title=" in build_snippet(Box(0, 0, "100x50", title="T"))


def test_snippet_reflects_a_later_mutation():
    label = Label(0, 0, "before")
    label.text = "after"
    assert "text='after'," in build_snippet(label)


def test_snippet_uses_raw_bg_so_it_round_trips():
    # Style stores a named bg with an internal "_bg" suffix; echoing that back
    # into Style(bg=...) would re-suffix it into "red_bg_bg".
    label = Label(0, 0, "x", Style(fg="cyan", bg="red", styles=["bold"]))
    snippet = build_snippet(label)
    assert "bg='red'" in snippet
    apply_snippet(label, snippet)  # unchanged round trip
    assert label.style.bg == "red_bg"


def test_a_clean_round_trip_reports_no_changes():
    label = Label(1, 1, "same")
    assert apply_snippet(label, build_snippet(label)) == []


# ── parsing ──────────────────────────────────────────────────────────────────


def test_parses_keyword_values():
    assert parse_snippet("Label(x=1, text='hi')") == {"x": 1, "text": "hi"}


def test_parses_a_nested_style():
    values = parse_snippet("Label(style=Style(fg='red', styles=['bold']))")
    style = values["style"]
    assert (style.fg, style.styles) == ("red", ("bold",))


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "not a call",
        "Label(1, 2)",  # positional
        "Label(**kwargs)",
        "Label(x=1",  # syntax error
    ],
)
def test_malformed_snippets_raise_edit_error(text):
    with pytest.raises(EditError):
        parse_snippet(text)


@pytest.mark.parametrize(
    "text",
    [
        "Label(text=__import__('os').system('echo hi'))",
        "Label(text=open('/etc/passwd').read())",
        "Label(text=some_name)",
        "Label(text=1 if print('x') else 2)",
        "Label(style=SomethingElse(fg='red'))",
        "Label(style=Style(fg=open('x')))",
    ],
)
def test_code_is_never_evaluated(text):
    # Structural parse + literal_eval only, like TermQuarium's Cheat Console:
    # a typed value can never call anything.
    with pytest.raises(EditError):
        parse_snippet(text)


def test_unknown_style_argument_is_rejected():
    with pytest.raises(EditError, match="underline"):
        parse_snippet("Label(style=Style(underline=True))")


# ── applying ─────────────────────────────────────────────────────────────────


def test_apply_mutates_the_live_widget():
    label = Label(3, 2, "Hello")
    changed = apply_snippet(label, "Label(x=8, text='Edited')")
    assert set(changed) == {"x", "text"}
    assert (label.x, label.text) == (8, "Edited")


def test_apply_reports_only_fields_that_really_changed():
    label = Label(3, 2, "Hello")
    assert apply_snippet(label, "Label(x=3, text='New')") == ["text"]


def test_apply_goes_through_property_setters():
    # ProgressBar.progress clamps; Text.text re-wraps. Binding through setattr
    # means an edit behaves exactly like a hand-written assignment.
    bar = ProgressBar(0, 0, progress=10, minimum=0, maximum=100)
    apply_snippet(bar, "ProgressBar(progress=500)")
    assert bar.get() == 100


def test_style_edits_apply():
    label = Label(0, 0, "x")
    apply_snippet(label, "Label(style=Style(fg='magenta', styles=['bold']))")
    assert label.style.fg == "magenta"
    assert label.style.styles == ("bold",)


def test_unknown_field_is_rejected_rather_than_silently_set():
    label = Label(0, 0, "x")
    with pytest.raises(EditError, match="isn't editable"):
        apply_snippet(label, "Label(txt='typo')")
    assert not hasattr(label, "txt")


def test_field_the_widget_lacks_is_rejected():
    with pytest.raises(EditError, match="has no"):
        apply_snippet(Label(0, 0, "x"), "Label(checked=True)")


def test_type_mismatch_is_rejected():
    label = Label(0, 0, "x")
    with pytest.raises(EditError, match="expects number"):
        apply_snippet(label, "Label(x='wide')")
    assert label.x == 0


def test_int_may_widen_to_float():
    label = Label(0, 0, "x")
    apply_snippet(label, "Label(x=4.5)")
    assert label.x == 4.5


def test_nothing_is_applied_when_a_later_field_is_invalid():
    # All-or-nothing: a half-applied edit on a UI you're looking at is
    # indistinguishable from one that worked.
    label = Label(1, 1, "original")
    with pytest.raises(EditError):
        apply_snippet(label, "Label(text='changed', x='oops')")
    assert (label.text, label.x) == ("original", 1)


# ── panel integration ────────────────────────────────────────────────────────


def _open_on(ui, widget):
    """Open DevTools with `widget` selected and frozen, and hand back the
    Elements view."""
    app = ui.app
    app.add(widget)
    ui.press(Key.F12)
    app._selected_widget = widget
    app._selection_seq += 1
    app._selection_frozen = True
    ui.compose()
    return app._devtools_panel.elements


def test_selecting_a_widget_fills_the_editor():
    ui = make_ui()
    app = ui.app
    label = Label(3, 2, "Hello")
    elements = _open_on(ui, label)
    assert "text='Hello'," in elements.editor.value
    assert "Live edit" in ui.screen


def test_editing_and_applying_changes_the_real_screen():
    ui = make_ui()
    app = ui.app
    label = Label(3, 2, "Hello")
    elements = _open_on(ui, label)

    elements.editor.value = "Label(x=3, y=2, text='Edited!')"
    elements._apply()
    ui.compose()

    assert label.text == "Edited!"
    assert "Edited!" in ui.screen
    assert "applied" in elements._message.text


def test_applying_refreshes_the_snippet_and_the_read_only_rows():
    ui = make_ui()
    app = ui.app
    label = Label(3, 2, "Hello")
    elements = _open_on(ui, label)
    elements.editor.value = "Label(x=9, text='Hi')"
    elements._apply()
    assert "x=9," in elements.editor.value  # re-synthesized from the widget
    ui.compose()
    assert "x: 9" in ui.screen  # the property list above it too


def test_a_bad_edit_reports_in_the_panel_without_raising():
    ui = make_ui()
    app = ui.app
    label = Label(3, 2, "Hello")
    elements = _open_on(ui, label)
    elements.editor.value = "Label(x='wide')"
    elements._apply()  # must not raise -- it runs from a Button callback
    ui.compose()
    assert label.x == 3
    assert "expects number" in elements._message.text


def test_revert_restores_the_widgets_current_snippet():
    ui = make_ui()
    app = ui.app
    label = Label(3, 2, "Hello")
    elements = _open_on(ui, label)
    elements.editor.value = "Label(text='never applied')"
    elements._revert()
    assert "text='Hello'," in elements.editor.value
    assert label.text == "Hello"


def test_editor_widgets_survive_a_rebuild():
    # They're built once and only repositioned -- otherwise a rebuild while the
    # editor was focused would leave App.focused pointing at an orphan.
    ui = make_ui()
    app = ui.app
    label = Label(3, 2, "Hello")
    elements = _open_on(ui, label)
    editor = elements.editor
    app._selected_widget = Label(0, 0, "other")
    app._selection_seq += 1
    ui.compose()
    assert elements.editor is editor
    assert editor in elements.children


def test_focusing_the_editor_freezes_the_selection():
    ui = make_ui()
    app = ui.app
    label = Label(3, 2, "Hello")
    elements = _open_on(ui, label)
    app._selection_frozen = False
    app._set_focused(elements.editor)
    ui.compose()
    assert app._selection_frozen is True


def test_escape_does_not_unfreeze_while_the_editor_is_focused():
    ui = make_ui()
    app = ui.app
    label = Label(3, 2, "Hello")
    elements = _open_on(ui, label)
    app._set_focused(elements.editor)
    ui.press(Key.ESC)
    assert app._selection_frozen is True  # the edit in progress is safe


def test_escape_still_unfreezes_when_the_editor_is_not_focused():
    ui = make_ui()
    app = ui.app
    label = Label(3, 2, "Hello")
    _open_on(ui, label)
    app._set_focused(None)
    ui.press(Key.ESC)
    assert app._selection_frozen is False


def test_no_editor_when_nothing_is_selected():
    ui = make_ui()
    app = ui.app
    app.add(Label(3, 2, "Hello"))
    ui.compose()
    ui.press(Key.F12)
    ui.compose()
    elements = app._devtools_panel.elements
    assert elements.editor not in elements.children
    assert "No widget selected" in ui.screen


def test_closing_devtools_clears_the_published_editor():
    ui = make_ui()
    app = ui.app
    _open_on(ui, Label(3, 2, "Hello"))
    assert app._devtools_editor is not None
    ui.press(Key.F12)
    assert app._devtools_editor is None


def test_the_editor_is_a_highlighted_code_input():
    # The snippet is Python, so it reads as source rather than as a text field.
    from cozy_tui.widgets import CodeInput

    ui = make_ui()
    app = ui.app
    elements = _open_on(ui, Label(3, 2, "Hello"))
    editor = elements.editor
    assert isinstance(editor, CodeInput)
    editor._sync()
    colors = {style.fg for row in editor._rows for _text, style in row}
    assert len(colors) > 1  # keywords/strings/numbers styled differently


def test_typing_in_the_editor_still_edits_normally():
    ui = make_ui()
    app = ui.app
    label = Label(3, 2, "Hello")
    elements = _open_on(ui, label)
    app._set_focused(elements.editor)
    elements.editor.value = ""
    for ch in "Label(x=6)":
        elements.editor.on_key(ch)
    elements._apply()
    assert label.x == 6
