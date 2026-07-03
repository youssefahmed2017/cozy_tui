import os

from cozy_tui import _console

# fmt: off
class Paste:
    """All text from a single terminal bracketed-paste event (ESC[200~...ESC[201~)."""
    def __init__(self, text: str):
        self.text = text

    def __repr__(self):
        return f"Paste({self.text!r})"


class MouseClick:
    """A mouse button press event with 0-indexed terminal coordinates."""
    def __init__(self, col: int, row: int, btn: int):
        self.col = col
        self.row = row
        self.btn = btn  # 0=left, 1=middle, 2=right

    def __repr__(self):
        return f"MouseClick(col={self.col}, row={self.row}, btn={self.btn})"


class MouseDrag:
    """Mouse motion while a button is held (drag), with 0-indexed coordinates."""
    def __init__(self, col: int, row: int, btn: int):
        self.col = col
        self.row = row
        self.btn = btn  # 0=left, 1=middle, 2=right

    def __repr__(self):
        return f"MouseDrag(col={self.col}, row={self.row}, btn={self.btn})"


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
    SHIFT_HOME        = "SHIFT_HOME"
    SHIFT_END         = "SHIFT_END"
    CTRL_LEFT         = "CTRL_LEFT"
    CTRL_RIGHT        = "CTRL_RIGHT"
    CTRL_SHIFT_LEFT   = "CTRL_SHIFT_LEFT"
    CTRL_SHIFT_RIGHT  = "CTRL_SHIFT_RIGHT"
    CTRL_U            = "\x15"
    CTRL_Y            = "\x19"
    INSERT            = "INSERT"

    F1  = "F1"
    F2  = "F2"
    F3  = "F3"
    F4  = "F4"
    F5  = "F5"
    F6  = "F6"
    F7  = "F7"
    F8  = "F8"
    F9  = "F9"
    F10 = "F10"
    F11 = "F11"
    F12 = "F12"

    # Modifier prefixes. Terminals never send a lone Alt/Ctrl press — only in
    # combination with another key — so these are used through the helpers below.
    ALT  = "alt"
    CTRL = "ctrl"

    @staticmethod
    def alt(key: str) -> str:
        """Key value for Alt+<key>: Key.alt('s') == 'alt+s', Key.alt(Key.F5) == 'alt+F5'."""
        return "alt+" + key

    @staticmethod
    def shift(key: str) -> str:
        """Key value for Shift+<key> (used with F-keys): Key.shift(Key.F5) == 'shift+F5'."""
        return "shift+" + key

    @staticmethod
    def ctrl(key: str) -> str:
        r"""Key value for Ctrl+<key>. A single letter maps to the actual control
        byte the terminal sends (Key.ctrl('a') == Key.CTRL_A == '\x01'); anything
        else (e.g. an F-key) becomes a 'ctrl+<key>' string."""
        if len(key) == 1 and key.isalpha():
            return chr(ord(key.lower()) & 0x1F)
        return "ctrl+" + key

    @staticmethod
    def label(token: str) -> str:
        r"""Human-readable label for a key token — the inverse of the constants
        and helpers. E.g. Key.label(Key.ESC) == 'Esc', Key.label(Key.UP) == '↑',
        Key.label(Key.ctrl('f')) == 'Ctrl+F', Key.label('alt+s') == 'Alt+S'."""
        if token in _KEY_LABELS:
            return _KEY_LABELS[token]
        if "+" in token:  # modifier combos: alt+x, ctrl+F5, ctrl+shift+F12
            *mods, key = token.split("+")
            pretty = [m.capitalize() for m in mods]
            pretty.append(key.upper() if len(key) == 1 else key.title())
            return "+".join(pretty)
        if len(token) == 1 and 1 <= ord(token) <= 26:  # Ctrl+<letter> control byte
            return "Ctrl+" + chr(ord(token) + 64)
        return token
# fmt: on


# Pretty labels for named / special key tokens (control bytes that would
# otherwise become "Ctrl+X" are listed here so they read correctly).
_KEY_LABELS = {
    Key.ESC: "Esc",
    Key.ENTER: "Enter",
    Key.TAB: "Tab",
    Key.BACKSPACE: "Backspace",
    "\x7f": "Backspace",
    " ": "Space",
    Key.UP: "↑", Key.DOWN: "↓", Key.LEFT: "←", Key.RIGHT: "→",
    Key.HOME: "Home", Key.END: "End",
    Key.DELETE: "Del", Key.INSERT: "Ins",
    Key.PAGE_UP: "PgUp", Key.PAGE_DOWN: "PgDn",
    Key.SHIFT_TAB: "Shift+Tab", Key.SHIFT_ENTER: "Shift+Enter",
    Key.SHIFT_LEFT: "Shift+←", Key.SHIFT_RIGHT: "Shift+→",
    Key.SHIFT_UP: "Shift+↑", Key.SHIFT_DOWN: "Shift+↓",
    Key.SHIFT_HOME: "Shift+Home", Key.SHIFT_END: "Shift+End",
    Key.CTRL_UP: "Ctrl+↑", Key.CTRL_DOWN: "Ctrl+↓",
    Key.CTRL_LEFT: "Ctrl+←", Key.CTRL_RIGHT: "Ctrl+→",
    Key.CTRL_SHIFT_LEFT: "Ctrl+Shift+←", Key.CTRL_SHIFT_RIGHT: "Ctrl+Shift+→",
    Key.SCROLL_UP: "Scroll↑", Key.SCROLL_DOWN: "Scroll↓",
}

# Internal read buffer.  We bulk-read from stdin on every refill so that a full
# VT sequence (e.g. ESC [ A) lands in _buf all at once, making the ESC-vs-CSI
# disambiguation reliable — separate from the OS-level input readiness that
# _console.kbhit() reports.
_buf: list[str] = []


def kbhit() -> bool:
    if _buf:
        return True
    return _console.kbhit()


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
    "2~": Key.INSERT,
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
    "1;5C": Key.CTRL_RIGHT,
    "1;5D": Key.CTRL_LEFT,
    "1;6C": Key.CTRL_SHIFT_RIGHT,
    "1;6D": Key.CTRL_SHIFT_LEFT,
    # Function keys. F5–F12 are always CSI "~" sequences; F1–F4 usually arrive as
    # SS3 (see _read_ss3) but some terminals send the CSI forms below.
    "11~": Key.F1, "12~": Key.F2, "13~": Key.F3, "14~": Key.F4,
    "15~": Key.F5, "17~": Key.F6, "18~": Key.F7, "19~": Key.F8,
    "20~": Key.F9, "21~": Key.F10, "23~": Key.F11, "24~": Key.F12,
    "1P": Key.F1, "1Q": Key.F2, "1R": Key.F3, "1S": Key.F4,
    # Ctrl+Shift+Z via XTerm modifyOtherKeys level 1 (\033[>4;1m):
    # Z=90 or z=122, Ctrl+Shift modifier=6
    "90;6u": Key.CTRL_Y,
    "122;6u": Key.CTRL_Y,
    "13;2u": Key.SHIFT_ENTER,  # XTerm / Windows Terminal Shift+Enter
}

# Function-key codes used for *modified* forms (CSI <code> ; <mod> ~ and
# CSI 1 ; <mod> P/Q/R/S). Unmodified forms live in _CSI_MAP above.
_FKEY_TILDE = {
    "11": Key.F1, "12": Key.F2, "13": Key.F3, "14": Key.F4,
    "15": Key.F5, "17": Key.F6, "18": Key.F7, "19": Key.F8,
    "20": Key.F9, "21": Key.F10, "23": Key.F11, "24": Key.F12,
}
_FKEY_SS3 = {"P": Key.F1, "Q": Key.F2, "R": Key.F3, "S": Key.F4}


def _mod_prefix(mod: int) -> str:
    """Turn a CSI modifier number (1 + bitmask) into a 'ctrl+alt+shift+' prefix."""
    bits = mod - 1
    prefix = ""
    if bits & 4:
        prefix += "ctrl+"
    if bits & 2:
        prefix += "alt+"
    if bits & 1:
        prefix += "shift+"
    return prefix


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
        if btn & 32:  # motion with button held (drag); bit 32 is the motion flag
            if pressed:
                return MouseDrag(col - 1, row - 1, btn & 3)
            return None
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

    # XTerm modifyOtherKeys / kitty keyboard: ESC [ codepoint ; modifier u
    # Windows Terminal sends these when \033[>4;1m is active.  Map modified
    # letter keys back to their expected constants so existing handlers work.
    if buf.endswith("u") and ";" in buf:
        try:
            cp, mod = (int(x) for x in buf[:-1].split(";", 1))
        except ValueError:
            return None
        # Ctrl+Shift+Z (modifier 6, codepoint 90='Z' or 122='z') → treat as redo
        if mod == 6 and cp in (90, 122):
            return Key.CTRL_Y
        # Ctrl+letter or Ctrl+Shift+letter → ASCII control code (chr(cp % 32))
        # Covers a-z (97-122) and A-Z (65-90); cp % 32 gives 1-26.
        if mod in (5, 6) and (65 <= cp <= 90 or 97 <= cp <= 122):
            return chr(cp % 32)
        # Alt (3) or Alt+Shift (4) + printable → "alt+<char>"
        if mod in (3, 4) and cp >= 0x20:
            return Key.alt(chr(cp))
        if mod == 1:
            return Key.BACKSPACE if cp == 127 else chr(cp)
        return None

    # Bracketed paste: ESC [ 200 ~ ... ESC [ 201 ~
    if buf == "200~":
        chars = []
        while True:
            c = _read_char()
            if c == "\x1b":
                c2 = _read_char()
                if c2 == "[":
                    seq = ""
                    while True:
                        sc = _read_char()
                        seq += sc
                        if sc.isalpha() or sc == "~":
                            break
                    if seq == "201~":
                        break
                    chars.append("\x1b[" + seq)
                else:
                    chars.append("\x1b")
                    chars.append(c2)
            else:
                chars.append(c)
        return Paste("".join(chars))

    # Modified function keys → "ctrl+F5", "shift+F5", "ctrl+shift+F5", …
    #   F5–F12 / legacy F1–F4:  CSI <code> ; <mod> ~
    #   F1–F4 (xterm):          CSI 1 ; <mod> P/Q/R/S
    if buf.endswith("~") and ";" in buf:
        code, _, mod = buf[:-1].partition(";")
        if code in _FKEY_TILDE and mod.isdigit():
            return _mod_prefix(int(mod)) + _FKEY_TILDE[code]
    elif buf[-1:] in ("P", "Q", "R", "S") and buf.startswith("1;"):
        mod = buf[2:-1]
        if mod.isdigit():
            return _mod_prefix(int(mod)) + _FKEY_SS3[buf[-1]]

    return _CSI_MAP.get(buf)


# SS3 payload byte → Key. F1–F4, plus arrows/Home/End in application cursor mode.
_SS3_MAP = {
    "P": Key.F1, "Q": Key.F2, "R": Key.F3, "S": Key.F4,
    "A": Key.UP, "B": Key.DOWN, "C": Key.RIGHT, "D": Key.LEFT,
    "H": Key.HOME, "F": Key.END,
}


def _read_ss3():
    """Classify an SS3 sequence (ESC O already consumed)."""
    return _SS3_MAP.get(_read_char())


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
        if ch2 == "O":  # SS3 — F1–F4 and application-mode cursor keys
            return _read_ss3()
        if ch2 == "\r":  # Windows Terminal sends ESC+CR for Shift+Enter
            return Key.SHIFT_ENTER
        if ch2 == "\x7f":  # ESC + DEL → Alt+Backspace
            return Key.alt("backspace")
        if len(ch2) == 1 and ch2.isprintable():
            return Key.alt(ch2)  # ESC + <char> → Alt+<char>
        return Key.ESC
    return ch
