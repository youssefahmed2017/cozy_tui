from collections import deque

import cozy_tui.events as ev
from cozy_tui.events import Key


def feed(seq: str):
    """Prime the internal read buffer with a full byte sequence and parse one key.
    The buffer holds the whole sequence, so os.read (stdin) is never touched."""
    ev._buf = deque(seq)
    return ev.read_key()


# ── constants / helpers ──────────────────────────────────────────────────────


def test_fkey_constants_exist():
    assert Key.F1 == "F1" and Key.F12 == "F12"


def test_alt_helper():
    assert Key.ALT == "alt"
    assert Key.alt("s") == "alt+s"


def test_ctrl_helper_matches_control_bytes():
    assert Key.CTRL == "ctrl"
    assert Key.ctrl("a") == "\x01" == Key.CTRL_A
    assert Key.ctrl("C") == "\x03" == Key.CTRL_C  # case-insensitive


# ── parsing ──────────────────────────────────────────────────────────────────


def test_ss3_function_keys():
    assert feed("\x1bOP") == Key.F1
    assert feed("\x1bOQ") == Key.F2
    assert feed("\x1bOR") == Key.F3
    assert feed("\x1bOS") == Key.F4


def test_ss3_application_cursor_keys():
    assert feed("\x1bOA") == Key.UP
    assert feed("\x1bOD") == Key.LEFT


def test_csi_function_keys():
    assert feed("\x1b[15~") == Key.F5
    assert feed("\x1b[17~") == Key.F6
    assert feed("\x1b[21~") == Key.F10
    assert feed("\x1b[24~") == Key.F12
    assert feed("\x1b[11~") == Key.F1  # legacy CSI form


def test_modified_function_keys_tilde():
    assert feed("\x1b[15;5~") == "ctrl+F5"  # Ctrl+F5
    assert feed("\x1b[15;2~") == "shift+F5"  # Shift+F5
    assert feed("\x1b[15;3~") == "alt+F5"  # Alt+F5
    assert feed("\x1b[24;6~") == "ctrl+shift+F12"  # Ctrl+Shift+F12
    assert feed("\x1b[15;7~") == "ctrl+alt+F5"  # Ctrl+Alt+F5


def test_modified_function_keys_ss3_form():
    assert feed("\x1b[1;5P") == "ctrl+F1"  # Ctrl+F1 (xterm CSI form)
    assert feed("\x1b[1;2S") == "shift+F4"  # Shift+F4


def test_modifier_helpers_compose_for_fkeys():
    assert Key.ctrl(Key.F5) == "ctrl+F5"
    assert Key.alt(Key.F5) == "alt+F5"
    assert Key.shift(Key.F5) == "shift+F5"
    assert Key.ctrl(Key.shift(Key.F12)) == "ctrl+shift+F12"  # canonical order


def test_alt_letter_via_esc_prefix():
    assert feed("\x1ba") == Key.alt("a") == "alt+a"
    assert feed("\x1bX") == "alt+X"


def test_alt_backspace():
    assert feed("\x1b\x7f") == "alt+backspace"


def test_alt_via_modify_other_keys():
    # ESC [ 97 ; 3 u  == Alt+a in the kitty/xterm modifyOtherKeys encoding
    assert feed("\x1b[97;3u") == "alt+a"


def test_csi_u_unmodified_keys_without_a_modifier_field():
    # WezTerm / kitty / GNOME (kitty keyboard protocol) send unmodified keys as
    # `CSI code u` with no `;modifier` — Esc must still map to Key.ESC (else the
    # quit handler never fires and the terminal is left with mouse tracking on).
    assert feed("\x1b[27u") == Key.ESC
    assert feed("\x1b[13u") == Key.ENTER
    assert feed("\x1b[97u") == "a"


def test_csi_u_ignores_key_release_events():
    # kitty protocol appends `:event`; 3 = release. Act on press only.
    assert feed("\x1b[97;1:3u") is None
    assert feed("\x1b[97;1:1u") == "a"  # explicit press event


def test_csi_u_modified_keys_still_map():
    assert feed("\x1b[122;6u") == Key.CTRL_Y  # Ctrl+Shift+Z → redo
    assert feed("\x1b[97;5u") == Key.ctrl("a")  # Ctrl+A


def test_ctrl_byte_passthrough():
    assert feed("\x06") == Key.ctrl("f")  # Ctrl+F arrives as raw 0x06


def test_lone_escape_still_escape(monkeypatch):
    # A lone ESC empties _buf, so read_key() falls through to _console.wait_input()
    # to check for a pending continuation. Force "nothing pending" deterministically
    # instead of racing the real stdin fd's state under the test runner.
    monkeypatch.setattr(ev._console, "wait_input", lambda timeout: False)
    assert feed("\x1b") == Key.ESC


def test_plain_char_unchanged():
    assert feed("a") == "a"
    assert feed("\r") == Key.ENTER


def test_key_label_named_and_arrows():
    assert Key.label(Key.ESC) == "Esc"
    assert Key.label(Key.ENTER) == "Enter"
    assert Key.label(Key.UP) == "↑"
    assert Key.label(Key.LEFT) == "←"
    assert Key.label(Key.PAGE_DOWN) == "PgDn"
    assert Key.label(Key.F5) == "F5"


def test_key_label_modifiers():
    assert Key.label(Key.ctrl("f")) == "Ctrl+F"  # control byte \x06
    assert Key.label(Key.CTRL_C) == "Ctrl+C"
    assert Key.label(Key.alt("s")) == "Alt+S"
    assert Key.label("ctrl+shift+F12") == "Ctrl+Shift+F12"
    assert Key.label(" ") == "Space"


def test_key_label_plain_char_and_fallback():
    assert Key.label("a") == "a"
    assert Key.label("?") == "?"
