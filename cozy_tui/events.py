import os
import ctypes as _ct

_k32 = _ct.windll.kernel32
_h_stdin = _k32.GetStdHandle(_ct.c_ulong(-10))  # STD_INPUT_HANDLE

# fmt: off
class MouseClick:
    """A mouse button press event with 0-indexed terminal coordinates."""
    def __init__(self, col: int, row: int, btn: int):
        self.col = col
        self.row = row
        self.btn = btn  # 0=left, 1=middle, 2=right

    def __repr__(self):
        return f"MouseClick(col={self.col}, row={self.row}, btn={self.btn})"


class Key:
    ESC        = "\x1b"
    ENTER      = "\r"
    BACKSPACE  = "\x08"
    TAB        = "\t"
    UP         = "UP"
    DOWN       = "DOWN"
    LEFT       = "LEFT"
    RIGHT      = "RIGHT"
    DELETE     = "DELETE"
    HOME       = "HOME"
    END        = "END"
    PAGE_UP    = "PAGE_UP"
    PAGE_DOWN  = "PAGE_DOWN"
    CTRL_UP    = "CTRL_UP"
    CTRL_DOWN  = "CTRL_DOWN"
    SCROLL_UP  = "SCROLL_UP"
    SCROLL_DOWN = "SCROLL_DOWN"
    CTRL_C      = "\x03"
    CTRL_A      = "\x01"
    CTRL_V      = "\x16"
    CTRL_X      = "\x18"
    SHIFT_TAB   = "SHIFT_TAB"
    SHIFT_ENTER = "SHIFT_ENTER"
    SHIFT_LEFT  = "SHIFT_LEFT"
    SHIFT_RIGHT = "SHIFT_RIGHT"
    SHIFT_UP    = "SHIFT_UP"
    SHIFT_DOWN  = "SHIFT_DOWN"
    SHIFT_HOME  = "SHIFT_HOME"
    SHIFT_END   = "SHIFT_END"
# fmt: on

# Internal read buffer.  os.read() reads the VT-processed byte stream while
# msvcrt.kbhit() peeks the raw event queue — different buffers.  We do a
# bulk read on every refill so that a full VT sequence (e.g. ESC [ A) lands
# in _buf all at once, making the ESC-vs-sequence disambiguation reliable.
_buf: list[str] = []


def kbhit() -> bool:
    if _buf:
        return True
    # WaitForSingleObject with 0ms timeout: returns 0 (WAIT_OBJECT_0) when stdin
    # has any pending input — keyboard, mouse clicks, or mouse scroll VT bytes.
    # msvcrt.kbhit() only detects KEY_EVENT records and misses mouse scroll in
    # Windows Terminal (ConPTY), where mouse events arrive as raw pipe bytes.
    return _k32.WaitForSingleObject(_h_stdin, 0) == 0


def _read_char() -> str:
    """Return one character, doing a bulk read from stdin if the buffer is empty."""
    global _buf
    if _buf:
        return _buf.pop(0)
    raw = os.read(0, 1024)  # reads ALL currently available bytes
    chars = list(raw.decode("utf-8", errors="replace"))
    if not chars:
        return ""
    _buf = chars[1:]
    return chars[0]


# CSI final-byte → Key constant
_CSI_MAP = {
    "A": Key.UP,
    "B": Key.DOWN,
    "C": Key.RIGHT,
    "D": Key.LEFT,
    "H": Key.HOME,
    "F": Key.END,
    "Z": Key.SHIFT_TAB,
    "3~": Key.DELETE,
    "3;1~": Key.DELETE,  # Windows Terminal: explicit "no modifier" variant
    "5~": Key.PAGE_UP,
    "6~": Key.PAGE_DOWN,
    "1;2A": Key.SHIFT_UP,
    "1;2B": Key.SHIFT_DOWN,
    "1;2C": Key.SHIFT_RIGHT,
    "1;2D": Key.SHIFT_LEFT,
    "1;2H": Key.SHIFT_HOME,
    "1;2F": Key.SHIFT_END,
    "1;5A": Key.CTRL_UP,
    "1;5B": Key.CTRL_DOWN,
    "13;2u": Key.SHIFT_ENTER,  # XTerm / Windows Terminal Shift+Enter
}


def _read_csi():
    """Read and classify a CSI sequence (ESC [ already consumed)."""
    buf = ""
    while True:
        c = _read_char()
        buf += c
        if c.isalpha() or c == "~":
            break

    # SGR mouse:  ESC [ < btn ; col ; row M/m
    if buf.startswith("<") and buf[-1] in ("M", "m"):
        pressed = buf[-1] == "M"
        try:
            parts = buf[1:-1].split(";")
            btn, col, row = int(parts[0]), int(parts[1]), int(parts[2])
        except (ValueError, IndexError):
            return None
        if btn == 64:
            return Key.SCROLL_UP
        if btn == 65:
            return Key.SCROLL_DOWN
        if pressed:
            return MouseClick(col - 1, row - 1, btn)  # SGR is 1-indexed
        return None

    # X10 mouse:  ESC [ M <3 raw bytes>
    if buf == "M":
        raw = ord(_read_char()) - 32
        col = ord(_read_char()) - 33
        row = ord(_read_char()) - 33
        if raw == 64:
            return Key.SCROLL_UP
        if raw == 65:
            return Key.SCROLL_DOWN
        if raw & 0x60 == 0:
            return MouseClick(col, row, raw & 0x03)
        return None

    # Catch all Delete variants: 3~, 3;1~, 3;2~, etc.
    if buf.startswith("3") and buf.endswith("~"):
        return Key.DELETE

    return _CSI_MAP.get(buf)


def read_key():
    ch = _read_char()
    if ch == "\x7f":  # DEL char — Windows Terminal sends this for Backspace
        return Key.BACKSPACE
    if ch == "\x1b":
        # After a bulk read, _buf will contain the rest of a VT sequence if
        # one was present.  An empty _buf means a standalone ESC.
        if not _buf:
            return Key.ESC
        ch2 = _read_char()
        if ch2 == "[":
            return _read_csi()
        if ch2 == "O":
            _read_char()  # SS3 payload (F1–F4) — consume and ignore
            return None
        if ch2 == "\r":  # Windows Terminal sends ESC+CR for Shift+Enter
            return Key.SHIFT_ENTER
        return Key.ESC
    return ch
