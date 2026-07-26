from cozy_tui._width import char_width, iter_cells, text_width


def test_ascii_is_single_width():
    for ch in "aZ0 .!":
        assert char_width(ch) == 1


def test_cjk_and_emoji_are_wide():
    assert char_width("あ") == 2  # Hiragana
    assert char_width("中") == 2  # CJK ideograph
    assert char_width("가") == 2  # Hangul syllable
    assert char_width("\U0001f600") == 2  # emoji


def test_transport_and_extended_emoji_are_wide():
    # Blocks the table used to miss, causing off-by-one alignment (e.g. menu icons).
    assert char_width("🚪") == 2  # U+1F6AA door — Transport & Map Symbols
    assert char_width("🚀") == 2  # U+1F680 rocket
    assert char_width("🩹") == 2  # U+1FA79 bandage — Symbols & Pictographs Extended-A


def test_combining_and_zero_width():
    assert char_width("́") == 0  # combining acute accent
    assert char_width("​") == 0  # zero-width space
    assert char_width("\n") == 0  # control char


def test_text_width_sums_display_columns():
    assert text_width("abc") == 3
    assert text_width("aあb") == 4  # 1 + 2 + 1
    assert text_width("é") == 1  # base + combining mark


def test_emoji_variation_selector_forces_width_2():
    # U+2744 SNOWFLAKE is a default-text symbol (width 1 on its own); the
    # trailing U+FE0F (VS16) forces emoji presentation, which the terminal
    # draws in two columns. The base char alone would mis-measure as 1.
    assert char_width("❄") == 1
    assert text_width("❄️") == 2  # snowflake + VS16
    assert text_width("a❄️b") == 4  # 1 + 2 + 1


def test_text_variation_selector_keeps_width_1():
    # VS15 forces *text* presentation, so the base is drawn single-column.
    assert text_width("❄︎") == 1


def test_iter_cells_merges_base_and_selector():
    cells = list(iter_cells("a❄️b"))
    assert cells == [("a", 1), ("❄️", 2), ("b", 1)]
