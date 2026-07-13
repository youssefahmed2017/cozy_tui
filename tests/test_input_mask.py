"""Input's digit-mask mechanism (mask="####-####-####-####"): the pure
mask_* helper functions, typing/backspace/delete/paste through Input itself,
selection-replace, the multiline guard, and the "Incomplete" validation
state."""

import pytest

from cozy_tui.events import Key, Paste
from cozy_tui.widgets import Input
from cozy_tui.widgets.input._input_mask import (
    mask_digit_count,
    mask_format,
    mask_pos_for_raw_index,
    mask_raw,
    mask_raw_index_at,
)

CARD_MASK = "####-####-####-####"


def make_masked(**kw):
    return Input(2, 1, 24, mask=CARD_MASK, **kw)


# ── pure helper functions ─────────────────────────────────────────────────────


def test_mask_digit_count():
    assert mask_digit_count(CARD_MASK) == 16


def test_mask_format_empty():
    assert mask_format(CARD_MASK, "") == ""


def test_mask_format_mid_group_no_trailing_dash():
    assert mask_format(CARD_MASK, "411") == "411"


def test_mask_format_shows_dash_immediately_after_fourth_digit():
    assert mask_format(CARD_MASK, "4111") == "4111-"


def test_mask_format_full():
    assert mask_format(CARD_MASK, "4111111111111111") == "4111-1111-1111-1111"


def test_mask_raw_recovers_digits_from_a_formatted_value():
    assert mask_raw(CARD_MASK, "4111-1111-1111-1111") == "4111111111111111"
    assert mask_raw(CARD_MASK, "4111-11") == "411111"
    assert mask_raw(CARD_MASK, "") == ""


def test_mask_raw_index_at():
    assert mask_raw_index_at(CARD_MASK, 0) == 0
    assert mask_raw_index_at(CARD_MASK, 4) == 4  # right after 4 digits, before "-"
    assert (
        mask_raw_index_at(CARD_MASK, 5) == 4
    )  # right after "-" -- still 4 digits precede


def test_mask_pos_for_raw_index_hops_past_the_new_separator():
    formatted = mask_format(CARD_MASK, "4111")
    assert mask_pos_for_raw_index(CARD_MASK, 4, formatted) == len(formatted)


def test_mask_pos_for_raw_index_mid_group():
    formatted = mask_format(CARD_MASK, "411")
    assert mask_pos_for_raw_index(CARD_MASK, 3, formatted) == 3


# ── typing through Input ──────────────────────────────────────────────────────


def test_typing_a_full_card_number_inserts_dashes_after_every_fourth_digit():
    inp = make_masked()
    for ch in "4111111111111111":
        inp.on_key(ch)
    assert inp.value == "4111-1111-1111-1111"
    assert inp.cursor_pos == len(inp.value)


def test_seventeenth_digit_is_refused_once_complete():
    inp = make_masked()
    for ch in "4111111111111111":
        inp.on_key(ch)
    before = inp.value
    inp.on_key("9")
    assert inp.value == before


def test_non_digit_keystrokes_are_rejected():
    inp = make_masked()
    inp.on_key("a")
    inp.on_key("-")
    inp.on_key(" ")
    assert inp.value == ""


# ── backspace / delete ────────────────────────────────────────────────────────


def test_backspace_right_after_a_dash_removes_the_preceding_digit_and_collapses_it():
    inp = make_masked()
    inp.value = "4111-1111"
    inp.cursor_pos = 5  # right after the first "-"
    inp.on_key(Key.BACKSPACE)
    assert inp.value == "4111-111"
    assert inp.cursor_pos == 3


def test_delete_mirrors_backspace():
    inp = make_masked()
    inp.value = "4111-1111"
    inp.cursor_pos = 4  # right before the "-"
    inp.on_key(Key.DELETE)
    # deletes the digit right after the cursor's raw position (still index 4)
    assert mask_raw(CARD_MASK, inp.value) == "4111111"


def test_backspace_at_start_is_a_noop():
    inp = make_masked()
    inp.value = "4111"
    inp.cursor_pos = 0
    inp.on_key(Key.BACKSPACE)
    assert inp.value == "4111"


# ── paste ─────────────────────────────────────────────────────────────────────


def test_paste_raw_digits_formats_them():
    inp = make_masked()
    inp.on_key(Paste("4111111111111111"))
    assert inp.value == "4111-1111-1111-1111"


def test_paste_already_formatted_text_produces_the_same_value():
    inp = make_masked()
    inp.on_key(Paste("4111-1111-1111-1111"))
    assert inp.value == "4111-1111-1111-1111"


def test_paste_beyond_capacity_truncates_instead_of_overflowing():
    inp = make_masked()
    inp.on_key(Paste("41111111111111119999"))
    assert inp.value == "4111-1111-1111-1111"


# ── selection replace ─────────────────────────────────────────────────────────


def test_typing_over_a_selection_replaces_just_the_selected_digits():
    inp = make_masked()
    inp.value = "4111-1111"
    inp._sel_anchor = 1
    inp.cursor_pos = 4
    inp.on_key("9")
    assert inp.value == "4911-11"


def test_backspace_with_a_selection_deletes_the_whole_selection():
    inp = make_masked()
    inp.value = "4111-1111"
    inp._sel_anchor = 1
    inp.cursor_pos = 4
    inp.on_key(Key.BACKSPACE)
    assert mask_raw(CARD_MASK, inp.value) == "41111"


# ── construction / validation ─────────────────────────────────────────────────


def test_mask_with_multiline_raises():
    with pytest.raises(ValueError):
        Input(2, 1, 24, mask=CARD_MASK, multiline=True)


def test_error_reports_incomplete_for_a_partial_touched_value():
    inp = make_masked()
    inp.on_key("4")
    assert inp.error == "Incomplete"


def test_error_is_none_when_untouched_even_if_empty():
    inp = make_masked()
    assert inp.error is None


def test_error_is_none_once_complete():
    inp = make_masked()
    for ch in "4111111111111111":
        inp.on_key(ch)
    assert inp.error is None


# ── unaffected behavior ───────────────────────────────────────────────────────


def test_navigation_and_select_all_still_work_normally():
    inp = make_masked()
    inp.value = "4111-1111"
    inp.cursor_pos = 9
    inp.on_key(Key.HOME)
    assert inp.cursor_pos == 0
    inp.on_key(Key.END)
    assert inp.cursor_pos == 9
    inp.on_key(Key.CTRL_A)
    assert inp._sel_range() == (0, 9)


def test_ctrl_c_still_copies_the_formatted_selection(monkeypatch):
    import cozy_tui.widgets.input._input_keys as keys_mod

    copied = []
    monkeypatch.setattr(keys_mod, "_clipboard_set", copied.append)
    inp = make_masked()
    inp.value = "4111-1111"
    inp.on_key(Key.CTRL_A)
    inp.on_key(Key.CTRL_C)
    assert copied == ["4111-1111"]
