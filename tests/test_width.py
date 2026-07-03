from cozy_tui._width import char_width, text_width


def test_ascii_is_single_width():
    for ch in "aZ0 .!":
        assert char_width(ch) == 1


def test_cjk_and_emoji_are_wide():
    assert char_width("あ") == 2  # Hiragana
    assert char_width("中") == 2  # CJK ideograph
    assert char_width("가") == 2  # Hangul syllable
    assert char_width("\U0001f600") == 2  # emoji


def test_combining_and_zero_width():
    assert char_width("́") == 0  # combining acute accent
    assert char_width("​") == 0  # zero-width space
    assert char_width("\n") == 0  # control char


def test_text_width_sums_display_columns():
    assert text_width("abc") == 3
    assert text_width("aあb") == 4  # 1 + 2 + 1
    assert text_width("é") == 1  # base + combining mark
