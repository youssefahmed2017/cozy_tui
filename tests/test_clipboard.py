from cozy_tui import clipboard


def test_copy_and_paste_never_raise():
    clipboard.copy("hello")
    assert isinstance(clipboard.paste(), str)


def test_backend_reports_a_known_name():
    assert clipboard.backend() in {
        "win32",
        "pbcopy",
        "wl-clipboard",
        "xclip",
        "xsel",
        "osc52",
    }
    # A named read/write backend implies availability; osc52 does not.
    assert clipboard.available() == (clipboard.backend() != "osc52")


def test_paste_always_returns_str():
    # Even with no functional backend (e.g. headless CI), paste yields a string.
    assert isinstance(clipboard.paste(), str)


def test_roundtrip_when_backend_available():
    if not clipboard.available():
        return  # no read/write backend on this machine — nothing to assert
    original = clipboard.paste()
    try:
        sample = "cozy-tui clipboard 测试 🎉"
        clipboard.copy(sample)
        assert clipboard.paste() == sample
    finally:
        clipboard.copy(original)  # be polite: restore the user's clipboard


def test_widget_adapter_delegates():
    from cozy_tui.widgets.input._input_clipboard import (
        _clipboard_get,
        _clipboard_set,
    )

    assert isinstance(_clipboard_get(), str)
    _clipboard_set("")  # empty is a no-op and must not raise
