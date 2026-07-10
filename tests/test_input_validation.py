import pytest

from cozy_tui import Theme, set_theme
from cozy_tui.events import Key
from cozy_tui.widgets import Input


def type_text(inp, text):
    for ch in text:
        inp.on_key(ch)


@pytest.fixture(autouse=True)
def _restore_default_theme():
    original = Theme()
    yield
    set_theme(original)


# ── inp_type="number" character filtering ────────────────────────────────────


def test_default_type_is_text_and_unrestricted():
    inp = Input(0, 0, 20)
    assert inp.type == "text"
    type_text(inp, "abc 123 !@#")
    assert inp.value == "abc 123 !@#"


def test_invalid_type_raises():
    with pytest.raises(ValueError):
        Input(0, 0, 20, inp_type="bogus")


def test_number_type_allows_digits_and_integers():
    inp = Input(0, 0, 20, inp_type="number")
    type_text(inp, "1012")
    assert inp.value == "1012"


def test_number_type_allows_one_decimal_point():
    inp = Input(0, 0, 20, inp_type="number")
    type_text(inp, "1.45")
    assert inp.value == "1.45"


def test_number_type_rejects_a_second_decimal_point():
    inp = Input(0, 0, 20, inp_type="number")
    type_text(inp, "1.3.66")
    assert inp.value == "1.366"  # the 2nd "." silently dropped


def test_number_type_rejects_letters_and_symbols():
    inp = Input(0, 0, 20, inp_type="number")
    type_text(inp, "abc123!@#")
    assert inp.value == "123"


def test_number_type_allows_leading_minus():
    inp = Input(0, 0, 20, inp_type="number")
    type_text(inp, "-5")
    assert inp.value == "-5"


def test_number_type_rejects_minus_mid_string():
    inp = Input(0, 0, 20, inp_type="number")
    type_text(inp, "5")
    inp.on_key("-")  # cursor is after "5", not at position 0
    assert inp.value == "5"


def test_number_type_filters_pasted_text():
    inp = Input(0, 0, 20, inp_type="number")
    inp._do_paste("12a.34.56b")
    assert inp.value == "12.3456"


def test_text_type_paste_is_unfiltered():
    inp = Input(0, 0, 20)
    inp._do_paste("hello world!")
    assert inp.value == "hello world!"


def test_overwrite_mode_respects_the_type_filter():
    inp = Input(0, 0, 20, inp_type="number")
    type_text(inp, "999")
    inp.on_key(Key.INSERT)  # toggle overwrite mode
    inp.on_key(Key.HOME)
    inp.on_key("a")  # rejected: not a digit
    assert inp.value == "999"
    inp.on_key("1")  # accepted: overwrites the first "9"
    assert inp.value == "199"


# ── required / touched ───────────────────────────────────────────────────────


def test_fresh_required_field_has_no_error():
    inp = Input(0, 0, 20, required=True)
    assert inp.error is None
    assert inp.is_valid is True


def test_required_field_errors_once_touched_and_empty():
    inp = Input(0, 0, 20, required=True)
    type_text(inp, "a")
    inp.on_key(Key.BACKSPACE)
    assert inp.value == ""
    assert inp.error == "Required"
    assert inp.is_valid is False


def test_required_field_valid_once_filled():
    inp = Input(0, 0, 20, required=True)
    type_text(inp, "hi")
    assert inp.error is None


# ── inp_type="number" + validation errors ────────────────────────────────────────


def test_number_in_progress_states_do_not_error():
    inp = Input(0, 0, 20, inp_type="number")
    inp.on_key("-")
    assert inp.error is None
    inp.on_key(".")
    assert inp.error is None  # "-." is a natural mid-typing state


def test_number_type_error_message_when_unparseable_somehow():
    # The character filter should normally prevent this, but error() must
    # still handle a value that isn't a "float()"-able number gracefully.
    inp = Input(0, 0, 20, inp_type="number")
    type_text(inp, "1")
    inp.value = "1x"  # bypass the filter directly, as a defensive check
    inp._touched = True
    assert inp.error == "Not a valid number"


# ── custom validator ──────────────────────────────────────────────────────────


def test_validator_false_gives_generic_message():
    inp = Input(0, 0, 20, validator=lambda v: len(v) >= 3)
    type_text(inp, "ab")
    assert inp.error == "Invalid"


def test_validator_string_is_used_as_the_message():
    inp = Input(0, 0, 20, validator=lambda v: "Too short" if len(v) < 3 else True)
    type_text(inp, "ab")
    assert inp.error == "Too short"


def test_validator_true_means_valid():
    inp = Input(0, 0, 20, validator=lambda v: True)
    type_text(inp, "anything")
    assert inp.error is None


def test_validator_only_runs_after_required_and_type_pass():
    calls = []

    def validator(v):
        calls.append(v)
        return True

    inp = Input(0, 0, 20, required=True, validator=validator)
    type_text(inp, "a")
    inp.on_key(Key.BACKSPACE)
    assert inp.error == "Required"
    assert calls == []  # validator never ran -- required already failed


# ── visual feedback ───────────────────────────────────────────────────────────


def test_valid_input_uses_normal_styles():
    inp = Input(0, 0, 20)
    assert inp._normal_style() is inp.style
    assert inp._focused_style().bg == "white_bg"


def test_invalid_input_tints_normal_and_focused_styles_with_theme_error_color():
    inp = Input(0, 0, 20, required=True)
    type_text(inp, "a")
    inp.on_key(Key.BACKSPACE)
    assert inp.error is not None
    theme = Theme()
    assert inp._normal_style().fg == theme.error
    assert inp._focused_style().bg == f"{theme.error}_bg"


def test_invalid_style_follows_the_active_theme():
    inp = Input(0, 0, 20, required=True)
    type_text(inp, "a")
    inp.on_key(Key.BACKSPACE)
    Theme(mode="monochromatic").activate()
    assert inp._normal_style().fg == Theme(mode="monochromatic").error


# ── error caching ─────────────────────────────────────────────────────────────


def test_error_does_not_re_invoke_validator_when_value_is_unchanged():
    calls = []

    def validator(v):
        calls.append(v)
        return True

    inp = Input(0, 0, 20, validator=validator)
    type_text(inp, "a")
    inp.error  # first read actually computes it
    assert len(calls) == 1
    for _ in range(10):  # simulates repeated draw() calls from animation/blink
        inp.error
    assert len(calls) == 1  # still just the one real change


def test_error_re_invokes_validator_after_a_real_change():
    calls = []

    def validator(v):
        calls.append(v)
        return True

    inp = Input(0, 0, 20, validator=validator)
    type_text(inp, "a")
    inp.error
    type_text(inp, "b")
    inp.error
    inp.error
    assert calls == ["a", "ab"]


def test_error_cache_also_keys_on_touched_not_just_value():
    # Both a freshly-untouched Input and one whose value has been edited back
    # to "" are self.value == "" -- the cache must still tell them apart via
    # _touched, or a required field's error would get stuck cached as None.
    inp = Input(0, 0, 20, required=True)
    assert inp.error is None  # untouched
    type_text(inp, "a")
    inp.on_key(Key.BACKSPACE)  # touched, now "" again
    assert inp.error == "Required"
