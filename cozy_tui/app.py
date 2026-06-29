import sys
import time
import os
import ctypes
from cozy_tui.style import Style, Cell
from cozy_tui.ansi import (
    _BG,
    _FG,
    _ST,
)
from cozy_tui.events import (
    Key,
    MouseClick,
    read_key,
    kbhit,
)

# fmt: off
_ENABLE_VT_INPUT        = 0x0200  # keyboard/mouse → VT sequences on stdin
_ENABLE_VT_PROCESSING   = 0x0004  # VT sequences honoured on stdout
_ENABLE_PROCESSED_INPUT = 0x0001  # Ctrl+C → CTRL_C_EVENT signal; must be OFF
_ENABLE_LINE_INPUT      = 0x0002  # line-buffered; must be OFF for raw mode
_ENABLE_ECHO_INPUT      = 0x0004  # echo; must be OFF for raw mode
# fmt: on


def _enable_vt_console():
    """Switch stdin to raw+VT mode; enable VT processing on stdout.
    Returns (old_in_mode, old_out_mode) for restoration."""
    try:
        k32 = ctypes.windll.kernel32
        h_in = k32.GetStdHandle(-10)
        h_out = k32.GetStdHandle(-11)
        m_in = ctypes.c_ulong()
        m_out = ctypes.c_ulong()
        k32.GetConsoleMode(h_in, ctypes.byref(m_in))
        k32.GetConsoleMode(h_out, ctypes.byref(m_out))
        raw_in = (
            m_in.value & ~(_ENABLE_PROCESSED_INPUT | _ENABLE_LINE_INPUT | _ENABLE_ECHO_INPUT)
        ) | _ENABLE_VT_INPUT
        k32.SetConsoleMode(h_in, raw_in)
        k32.SetConsoleMode(h_out, m_out.value | _ENABLE_VT_PROCESSING)
        return m_in.value, m_out.value
    except Exception:
        return None, None


def _restore_vt_console(old_in, old_out):
    try:
        k32 = ctypes.windll.kernel32
        if old_in is not None:
            k32.SetConsoleMode(k32.GetStdHandle(-10), old_in)
        if old_out is not None:
            k32.SetConsoleMode(k32.GetStdHandle(-11), old_out)
    except Exception:
        pass


class App:
    SCALE = 30
    BLINK_INTERVAL = 0.5

    def __init__(self, size, style: Style, full=True):
        self.style = style
        self.full = full
        self.scroll_y = 0
        self._content_rows = 0

        self._init_size(size)

        self.widgets = []
        self.focused = None
        self._key_handlers = {}
        self._cursor_on = True

    def _init_size(self, size=None):
        if self.full:
            try:
                term = os.get_terminal_size()
            except OSError:
                term = os.terminal_size((80, 24))
            self.cols = term.columns
            self.rows = term.lines
            self.width = self.cols * self.SCALE
            self.height = self.rows * self.SCALE
        else:
            self.width, self.height = map(int, size.split("x"))
            self.cols = self.width // self.SCALE
            self.rows = self.height // self.SCALE
        self._size_arg = size
        self.buffer = [
            [Cell(char=" ", style=self.style) for _ in range(self.cols)]
            for _ in range(self.rows)
        ]

    def _check_resize(self):
        if not self.full:
            return False
        try:
            term = os.get_terminal_size()
        except OSError:
            return False
        if term.columns == self.cols and term.lines == self.rows:
            return False
        self.cols = term.columns
        self.rows = term.lines
        self.width = self.cols * self.SCALE
        self.height = self.rows * self.SCALE
        self.buffer = [
            [Cell(char=" ", style=self.style) for _ in range(self.cols)]
            for _ in range(self.rows)
        ]
        max_scroll = max(0, self._content_rows - self.rows)
        self.scroll_y = min(self.scroll_y, max_scroll)
        return True

    def _scroll(self, delta):
        max_scroll = max(0, self._content_rows - self.rows)
        self.scroll_y = max(0, min(self.scroll_y + delta, max_scroll))

    def add(self, widget):
        self.widgets.append(widget)

    def on_key(self, key, handler):
        self._key_handlers[key] = handler

    def focus(self, widget):
        self.focused = widget

    def _collect_focusables(self):
        result = []

        def collect(the_widget):
            if the_widget.focusable:
                result.append(the_widget)
            if hasattr(the_widget, "children"):
                for child in the_widget.children:
                    collect(child)

        for widget in self.widgets:
            collect(widget)
        return result

    def _cycle_focus(self, direction=1):
        focusables = self._collect_focusables()
        if not focusables:
            return
        try:
            idx = focusables.index(self.focused)
        except ValueError:
            idx = -1
        self.focused = focusables[(idx + direction) % len(focusables)]

    def write(self, x, y, text, style: Style):
        # Track the furthest row any widget writes to for scroll clamping.
        if y + 1 > self._content_rows:
            self._content_rows = y + 1

        vy = y - self.scroll_y
        if not (0 <= vy < len(self.buffer)):
            return

        for i, ch in enumerate(text):
            col = x + i
            if 0 <= col < len(self.buffer[vy]):
                cell = self.buffer[vy][col]
                cell.char = ch
                cell.style = style

    def clear(self):
        self._content_rows = 0
        for row in self.buffer:
            for cell in row:
                cell.char = " "
                cell.style = self.style

    def render(self):
        self.clear()

        for widget in self.widgets:
            widget.draw(self)

        lines = []
        for row in self.buffer:
            parts = []
            prev_key = None
            run = []
            for cell in row:
                key = (cell.style.fg, cell.style.bg, tuple(cell.style.styles))
                if key != prev_key:
                    if run:
                        parts.append("".join(run))
                        run = []
                    codes = []
                    if cell.style.bg in _BG:
                        codes.append(_BG[cell.style.bg])
                    if cell.style.fg in _FG:
                        codes.append(_FG[cell.style.fg])
                    for s in cell.style.styles:
                        if s in _ST:
                            codes.append(_ST[s])
                    parts.append(f"\033[0;{';'.join(codes)}m" if codes else "\033[0m")
                    prev_key = key
                run.append(cell.char)
            if run:
                parts.append("".join(run))
            parts.append("\033[0m")
            lines.append("".join(parts))

        cursor_esc = "\033[?25l"
        focused = self.focused
        if (focused is not None
                and getattr(focused, "cursor", False)
                and getattr(focused, "cursor_style", None) == "vertical"
                and self._cursor_on):
            pos = focused._get_cursor_screen_pos(self.scroll_y)
            if pos is not None:
                sc, sr = pos
                if 0 <= sr < self.rows and 0 <= sc < self.cols:
                    cursor_esc = f"\033[{sr + 1};{sc + 1}H\033[?25h"

        sys.stdout.write("\033[H" + "\n".join(lines) + cursor_esc)
        sys.stdout.flush()

    def _hit_test(self, col: int, row: int):
        """Return the topmost focusable widget whose bounding box contains (col, row)."""

        def check(widget):
            if hasattr(widget, "children"):
                for child in widget.children:
                    result = check(child)
                    if result:
                        return result
            if widget.focusable and widget.contains(col, row):
                return widget
            return None

        for widget in reversed(self.widgets):
            result = check(widget)
            if result:
                return result
        return None

    def run(self):
        enter = (
            "\033[?1049h\033[2J\033[H\033[?25l\033[?1000h\033[?1006h"
            if self.full
            else "\033[2J\033[H\033[?25l\033[?1000h\033[?1006h"
        )

        exit_ = (
            "\033[?1006l\033[?1000l\033[?25h\033[?1049l"
            if self.full
            else "\033[?1006l\033[?1000l\033[?25h"
        )
        sys.stdout.write(enter)
        sys.stdout.flush()
        old_in, old_out = _enable_vt_console()
        try:
            while True:
                if self._check_resize():
                    pass  # buffer already rebuilt; fall through to render
                self.render()
                last_blink = time.monotonic()

                while not kbhit():
                    if self._check_resize():
                        self.render()
                        last_blink = time.monotonic()
                    elif time.monotonic() - last_blink >= self.BLINK_INTERVAL:
                        self._cursor_on = not self._cursor_on
                        self.render()
                        last_blink = time.monotonic()
                    time.sleep(0.02)

                self._cursor_on = True
                key = read_key()
                if key is None:
                    continue
                if isinstance(key, MouseClick):
                    target = self._hit_test(key.col, key.row + self.scroll_y)
                    if target is not None:
                        self.focused = target
                    continue
                if key == Key.CTRL_C:
                    break
                elif key in (Key.SCROLL_UP, Key.PAGE_UP, Key.CTRL_UP):
                    self._scroll(-3)
                elif key in (Key.SCROLL_DOWN, Key.PAGE_DOWN, Key.CTRL_DOWN):
                    self._scroll(3)
                elif key == Key.TAB:
                    self._cycle_focus(1)
                elif key == Key.SHIFT_TAB:
                    self._cycle_focus(-1)
                elif key in self._key_handlers:
                    if self._key_handlers[key]() == "quit":
                        break
                elif self.focused:
                    self.focused.on_key(key)
        except KeyboardInterrupt:
            pass
        finally:
            _restore_vt_console(old_in, old_out)
            sys.stdout.write(exit_)
            sys.stdout.flush()
