import cozy_tui.events as ev
from cozy_tui.events import Key


def feed(seq: str):
    """Prime the internal read buffer with a full byte sequence and parse one key.
    The buffer holds the whole sequence, so os.read (stdin) is never touched."""
    ev._buf = list(seq)
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


def test_alt_letter_via_esc_prefix():
    assert feed("\x1ba") == Key.alt("a") == "alt+a"
    assert feed("\x1bX") == "alt+X"


def test_alt_backspace():
    assert feed("\x1b\x7f") == "alt+backspace"


def test_alt_via_modify_other_keys():
    # ESC [ 97 ; 3 u  == Alt+a in the kitty/xterm modifyOtherKeys encoding
    assert feed("\x1b[97;3u") == "alt+a"


def test_ctrl_byte_passthrough():
    assert feed("\x06") == Key.ctrl("f")  # Ctrl+F arrives as raw 0x06


def test_lone_escape_still_escape():
    assert feed("\x1b") == Key.ESC


def test_plain_char_unchanged():
    assert feed("a") == "a"
    assert feed("\r") == Key.ENTER
