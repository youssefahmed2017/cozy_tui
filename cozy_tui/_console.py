"""Platform abstraction for raw terminal mode and input waiting.

`cozy_tui` was originally Windows-only. This module isolates the two things that
differ between platforms — entering/leaving raw+VT mode and blocking until input
is available — so the rest of the library (the VT-sequence parser in `events.py`
and the event loop in `app.py`) is portable. Everything else already speaks
plain ANSI/VT.

Public API (identical on every platform):
    enable_raw() -> state          # switch to raw+VT mode; returns a restore token
    restore(state) -> None         # undo enable_raw()
    kbhit() -> bool                # is input available right now?
    wait_input(timeout) -> bool    # block up to `timeout` seconds for input
"""

import sys

IS_WINDOWS = sys.platform == "win32"


if IS_WINDOWS:
    import ctypes

    _k32 = ctypes.windll.kernel32
    _H_IN = _k32.GetStdHandle(-10)
    _H_OUT = _k32.GetStdHandle(-11)

    _VT_INPUT = 0x0200
    _VT_PROCESSING = 0x0004
    _PROCESSED_INPUT = 0x0001
    _LINE_INPUT = 0x0002
    _ECHO_INPUT = 0x0004
    _MOUSE_INPUT = 0x0010
    _QUICK_EDIT_MODE = 0x0040
    _EXTENDED_FLAGS = 0x0080  # required before QuickEdit/mouse flags take effect

    def enable_raw():
        try:
            m_in = ctypes.c_ulong()
            m_out = ctypes.c_ulong()
            _k32.GetConsoleMode(_H_IN, ctypes.byref(m_in))
            _k32.GetConsoleMode(_H_OUT, ctypes.byref(m_out))
            # Disable QuickEdit (it steals the mouse for text selection) and enable
            # mouse input, so mouse events reach the app (translated to VT by
            # ?1000h/?1006h). Some terminals (WezTerm/ConPTY) drop mouse entirely
            # without this; Windows Terminal happens to forward it regardless.
            raw_in = (
                m_in.value
                & ~(_PROCESSED_INPUT | _LINE_INPUT | _ECHO_INPUT | _QUICK_EDIT_MODE)
            ) | _VT_INPUT | _MOUSE_INPUT | _EXTENDED_FLAGS
            _k32.SetConsoleMode(_H_IN, raw_in)
            _k32.SetConsoleMode(_H_OUT, m_out.value | _VT_PROCESSING)
            return (m_in.value, m_out.value)
        except Exception:
            return None

    def restore(state):
        if not state:
            return
        try:
            old_in, old_out = state
            _k32.SetConsoleMode(_H_IN, old_in)
            _k32.SetConsoleMode(_H_OUT, old_out)
        except Exception:
            pass

    def kbhit():
        # WaitForSingleObject with 0ms: signaled when stdin has any pending input
        # (keyboard, mouse click, or mouse-scroll VT bytes in ConPTY).
        return _k32.WaitForSingleObject(_H_IN, 0) == 0

    def wait_input(timeout):
        ms = max(0, int(timeout * 1000))
        return _k32.WaitForSingleObject(_H_IN, ms) == 0

else:  # POSIX (Linux, macOS, *BSD)
    import select
    import termios
    import tty

    def enable_raw():
        try:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            tty.setraw(fd)
            return old
        except Exception:
            return None

    def restore(state):
        if state is None:
            return
        try:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, state)
        except Exception:
            pass

    def kbhit():
        try:
            return bool(select.select([sys.stdin], [], [], 0)[0])
        except Exception:
            return False

    def wait_input(timeout):
        try:
            return bool(select.select([sys.stdin], [], [], max(0, timeout))[0])
        except Exception:
            return False
