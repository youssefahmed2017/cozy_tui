import os
import sys
import threading
import time
from collections import deque

from cozy_tui._console import enable_raw, restore, wait_input
from cozy_tui._dock import SIDES, dock_layout
from cozy_tui._width import char_width
from cozy_tui.ansi import style_esc
from cozy_tui.events import Key, MouseClick, MouseDrag, kbhit, read_key
from cozy_tui.style import Cell, Style

# Sentinel stored in _prev_cells to mark a cell that has never been rendered.
# Must not equal any valid (char, fg, bg, styles) tuple.
_UNSET = object()

# Longest the idle loop will block before re-checking terminal size / worker
# results, even when nothing else is due. Small enough to feel responsive,
# large enough that an idle app isn't busy-spinning.
_IDLE_POLL = 0.1

_RICH_WARNING = (
    "WARNING    Rich isn't installed so you won't get Markdown/MarkdownInput "
    "as real markdown."
)
_rich_warning_shown = False


def _warnings_suppressed() -> bool:
    """Whether COZY_TUI_NO_WARNINGS silences warnings. It defaults to on ("1"),
    so warnings are OFF by default; set it to a falsey value ("0", "false",
    "no", "off") to opt IN to warnings."""
    return os.environ.get("COZY_TUI_NO_WARNINGS", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _maybe_warn_rich() -> None:
    """Print a one-time warning to stderr on exit if `rich` is unavailable, so
    Markdown/MarkdownInput fall back to plain text silently-but-not-secretly.
    Off by default; enable with COZY_TUI_NO_WARNINGS=0."""
    global _rich_warning_shown
    if _rich_warning_shown or _warnings_suppressed():
        return
    try:
        from cozy_tui.widgets.display.markdown import _RICH_OK
    except Exception:
        _RICH_OK = False
    if not _RICH_OK:
        print(_RICH_WARNING, file=sys.stderr)
        _rich_warning_shown = True


class _Overlay:
    """A widget layered above the base UI. `modal` confines keyboard/mouse input
    to it (and, with `dim`, greys the background); a non-modal overlay is purely
    visual (e.g. a tooltip). `prev_focus` is restored when the overlay closes."""

    __slots__ = (
        "widget",
        "modal",
        "dim",
        "center",
        "close_on_escape",
        "close_on_click_outside",
        "on_close",
        "prev_focus",
    )

    def __init__(
        self,
        widget,
        modal,
        dim,
        center,
        close_on_escape,
        close_on_click_outside,
        on_close,
        prev_focus,
    ):
        self.widget = widget
        self.modal = modal
        self.dim = dim
        self.center = center
        self.close_on_escape = close_on_escape
        self.close_on_click_outside = close_on_click_outside
        self.on_close = on_close
        self.prev_focus = prev_focus


class App:
    SCALE = 10
    BLINK_INTERVAL = 0.5

    def __init__(
        self, style: Style = Style(bg="black", fg="white"), size=None, full=True
    ):
        self.style = style
        self.full = full
        self.scroll_y = 0
        self._content_rows = 0

        self._init_size(size)

        self.widgets = []
        self.focused = None
        self._key_handlers = {}
        self._cursor_on = True
        self._last_cursor_esc = None  # track last-emitted cursor state
        self._should_quit = False
        self.tick_interval: float | None = None  # set to e.g. 0.05 for animations
        # Results from background workers, delivered to the main thread by the
        # event loop so callbacks never touch the UI from another thread.
        self._worker_results: deque = deque()
        # Overlay/z-layer stack drawn above the base widgets (last == topmost).
        self._overlays: list[_Overlay] = []
        # write() honours scroll_y normally; overlays are screen-fixed, so it is
        # flipped off while they draw.
        self._scroll_active = True
        raw_bg = self.style.bg.replace("_bg", "") if self.style.bg else None
        self._backdrop_style = Style(fg="bright_black", bg=raw_bg)

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
        # Double buffer: stores the last-rendered (char, fg, bg, styles) per cell.
        # _UNSET marks cells that have never been written to the terminal.
        self._prev_cells = [[_UNSET] * self.cols for _ in range(self.rows)]
        self._full_render_pending = True
        self._last_cursor_esc = None

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
        self._prev_cells = [[_UNSET] * self.cols for _ in range(self.rows)]
        self._full_render_pending = True
        self._last_cursor_esc = None
        max_scroll = max(0, self._content_rows - self.rows)
        self.scroll_y = min(self.scroll_y, max_scroll)
        return True

    def _scroll(self, delta):
        max_scroll = max(0, self._content_rows - self.rows)
        self.scroll_y = max(0, min(self.scroll_y + delta, max_scroll))

    def add(self, widget):
        self.widgets.append(widget)

    def dock(self, widget, side, margin=0):
        """Dock `widget` to an edge of the screen.

        `side` is one of "left", "right", "top", "bottom", or "fill". Each dock
        consumes a band from the remaining screen rectangle (in call order) and
        the widget stretches across the other axis; "fill" takes whatever space
        is left. Docks are recomputed every frame, so they stay anchored across
        terminal resizes. `margin` insets the widget from the consumed edge.
        Returns the widget for chaining.
        """
        if side not in SIDES:
            raise ValueError(f"dock side must be one of {SIDES}, got {side!r}")
        widget._dock = (side, margin)
        if widget not in self.widgets:
            self.add(widget)
        return widget

    def _apply_docks(self):
        items = [
            (w, w._dock[0], w._dock[1])
            for w in self.widgets
            if getattr(w, "_dock", None) is not None
        ]
        if items:
            dock_layout(items, 0, 0, self.cols, self.rows, self.SCALE)

    # ── overlays / z-layer ──────────────────────────────────────────────────────

    def open_overlay(
        self,
        widget,
        *,
        modal=True,
        dim=True,
        center=True,
        close_on_escape=True,
        close_on_click_outside=False,
        on_close=None,
    ):
        """Push `widget` onto the overlay stack, drawn above everything else.

        A **modal** overlay confines keyboard focus and mouse input to itself
        (and, with `dim`, greys the background); a **non-modal** overlay is purely
        visual, e.g. a tooltip. `center` re-centres the widget on screen every
        frame (use a `Box` for a dialog). `close_on_escape` / `close_on_click_outside`
        give light dismissal. Overlays are screen-fixed (ignore scrolling).
        Returns `widget`.
        """
        widget.parent = None
        entry = _Overlay(
            widget,
            modal,
            dim,
            center,
            close_on_escape,
            close_on_click_outside,
            on_close,
            self.focused,
        )
        self._overlays.append(entry)
        if modal:
            self.focused = self._first_focusable(widget)
        self.invalidate()
        return widget

    def close_overlay(self, widget=None):
        """Close the topmost overlay, or the one wrapping `widget`. Restores the
        focus that was active when it opened and fires its `on_close(widget)`."""
        if not self._overlays:
            return
        if widget is None:
            entry = self._overlays.pop()
        else:
            entry = next((e for e in self._overlays if e.widget is widget), None)
            if entry is None:
                return
            self._overlays.remove(entry)
        self.focused = entry.prev_focus
        self.invalidate()
        if entry.on_close is not None:
            entry.on_close(entry.widget)

    def prompt(
        self,
        title,
        initial="",
        *,
        on_submit=None,
        on_cancel=None,
        width=40,
        close_on_click_outside=True,
    ):
        """Open a one-line text-entry modal. Enter calls ``on_submit(text)`` and
        closes; Esc or a click outside calls ``on_cancel()``. Returns the
        ``PromptDialog`` widget."""
        from cozy_tui.widgets.input.prompt import PromptDialog

        state = {"submitted": False}

        def _submit(text):
            state["submitted"] = True
            self.close_overlay(dialog)
            if on_submit is not None:
                on_submit(text)

        def _on_close(_widget):
            if not state["submitted"] and on_cancel is not None:
                on_cancel()

        dialog = PromptDialog(title, initial, on_submit=_submit, width=width, style=self.style)
        self.open_overlay(
            dialog,
            modal=True,
            dim=True,
            center=True,
            close_on_escape=True,
            close_on_click_outside=close_on_click_outside,
            on_close=_on_close,
        )
        return dialog

    def _topmost_modal(self):
        for entry in reversed(self._overlays):
            if entry.modal:
                return entry
        return None

    def _draw_overlays(self):
        if not self._overlays:
            return
        self._scroll_active = False  # overlays position in screen space
        try:
            for entry in self._overlays:
                if entry.dim:
                    self._apply_backdrop()
                if entry.center:
                    self._center(entry.widget)
                entry.widget.draw(self)
        finally:
            self._scroll_active = True

    def _apply_backdrop(self):
        """Grey every already-drawn cell (chars kept) as a scrim behind a modal."""
        style = self._backdrop_style
        for row in self.buffer:
            for cell in row:
                cell.style = style

    def _center(self, widget):
        w = widget.natural_width(self.SCALE)
        h = widget.natural_height(self.SCALE)
        widget.x = max(0, (self.cols - w) // 2)
        widget.y = max(0, (self.rows - h) // 2)

    def on_key(self, key, handler):
        self._key_handlers[key] = handler

    def focus(self, widget):
        self.focused = widget

    def invalidate(self):
        """Force a full render on the next frame — call after switching screens."""
        self._full_render_pending = True
        self._last_cursor_esc = None

    def run_worker(self, func, *args, on_result=None, on_error=None, **kwargs):
        """Run ``func(*args, **kwargs)`` on a background daemon thread so long
        operations don't block the UI. When it finishes, ``on_result(value)`` (or
        ``on_error(exc)`` if it raised) is invoked on the **main thread** by the
        event loop, followed by a re-render. Returns the started ``Thread``."""

        def _run():
            try:
                self._worker_results.append((on_result, func(*args, **kwargs)))
            except Exception as exc:  # delivered to on_error on the main thread
                self._worker_results.append((on_error, exc))

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread

    def _drain_workers(self):
        """Fire callbacks for finished workers on the main thread. Returns True
        if any fired (so the caller can re-render)."""
        fired = False
        while self._worker_results:
            callback, payload = self._worker_results.popleft()
            if callback is not None:
                callback(payload)
            fired = True
        return fired

    def _collect_focusables(self):
        # A modal overlay confines Tab to itself; otherwise cycle the base UI.
        modal = self._topmost_modal()
        roots = [modal.widget] if modal else self.widgets
        result = []
        for widget in roots:
            result.extend(self._focusables_in(widget))
        return result

    def _focusables_in(self, widget):
        """Ordered focus stops within `widget`. A focusable container defers to
        its focusable descendants — so Tab dives into the first child instead of
        stopping on the container — and is only a stop itself when it contains no
        focusable descendant (e.g. an empty or decorative Box)."""
        found = []
        kids = getattr(widget, "children", None)
        if kids:
            for child in kids:
                found.extend(self._focusables_in(child))
        if found:
            return found
        return [widget] if widget.focusable else []

    def _first_focusable(self, widget):
        """First focus stop within `widget`, diving through containers, or None."""
        stops = self._focusables_in(widget)
        return stops[0] if stops else None

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
        if self._scroll_active:
            if y + 1 > self._content_rows:
                self._content_rows = y + 1
            vy = y - self.scroll_y
        else:
            vy = y  # overlay pass: screen-fixed, no scroll offset or content growth
        if not (0 <= vy < len(self.buffer)):
            return
        row = self.buffer[vy]
        n = len(row)
        col = x
        for ch in text:
            w = char_width(ch)
            if w == 0:
                # Zero-width (combining marks, ZWJ, BOM): carries no column of
                # its own. Dropped rather than merged, which keeps the grid model
                # simple while preventing width desync.
                continue
            if col >= n:
                break
            if col >= 0:
                cell = row[col]
                cell.char = ch
                cell.style = style
                if w == 2:
                    # A wide glyph advances the terminal two columns. Blank the
                    # trailing cell so nothing is emitted there and the grid
                    # stays aligned; if it would fall off the row, clip to space.
                    if col + 1 < n:
                        cont = row[col + 1]
                        cont.char = ""
                        cont.style = style
                    else:
                        cell.char = " "
            col += w

    def clear(self):
        self._content_rows = 0
        base = self.style
        for row in self.buffer:
            for cell in row:
                cell.char = " "
                cell.style = base

    # ── rendering ─────────────────────────────────────────────────────────────

    def render(self):
        self.clear()
        self._apply_docks()
        for widget in self.widgets:
            widget.draw(self)
        self._draw_overlays()

        if self._full_render_pending:
            self._full_render_pending = False
            self._do_full_render()
        else:
            self._do_diff_render()

    def _cursor_esc(self) -> str:
        """Return the terminal escape to position / show / hide the cursor."""
        focused = self.focused
        if focused is None:
            return "\033[?25l"
        if not getattr(focused, "cursor", False):
            return "\033[?25l"
        style = getattr(focused, "cursor_style", None)
        if style not in ("vertical", "block"):
            return "\033[?25l"
        if not self._cursor_on:
            return "\033[?25l"
        # A focused widget inside a modal overlay is screen-fixed (no scroll).
        scroll = 0 if self._topmost_modal() else self.scroll_y
        pos = focused._get_cursor_screen_pos(scroll)
        if pos is None:
            return "\033[?25l"
        sc, sr = pos
        if 0 <= sr < self.rows and 0 <= sc < self.cols:
            shape = "\033[2 q" if style == "block" else "\033[6 q"
            return f"\033[{sr + 1};{sc + 1}H{shape}\033[?25h"
        return "\033[?25l"

    def _do_full_render(self):
        """Write every cell to the terminal and sync _prev_cells."""
        lines = []
        prev = self._prev_cells

        for r, row in enumerate(self.buffer):
            parts = []
            prev_style_key = None
            run = []
            prev_row = prev[r]

            for c, cell in enumerate(row):
                sk = cell.style.styles
                style_key = (cell.style.fg, cell.style.bg, sk)

                if style_key != prev_style_key:
                    if run:
                        parts.append("".join(run))
                        run = []
                    parts.append(style_esc(cell.style.fg, cell.style.bg, sk))
                    prev_style_key = style_key

                run.append(cell.char)
                prev_row[c] = (cell.char, cell.style.fg, cell.style.bg, sk)

            if run:
                parts.append("".join(run))
            parts.append("\033[0m")
            lines.append("".join(parts))

        cursor = self._cursor_esc()
        sys.stdout.write("\033[H" + "\n".join(lines) + cursor)
        sys.stdout.flush()
        self._last_cursor_esc = cursor

    def _do_diff_render(self):
        """Write only cells that changed since the last render."""
        out = []
        prev = self._prev_cells

        for r, row in enumerate(self.buffer):
            prev_row = prev[r]
            for c, cell in enumerate(row):
                sk = cell.style.styles
                key = (cell.char, cell.style.fg, cell.style.bg, sk)
                if key == prev_row[c]:
                    continue
                prev_row[c] = key
                out.append(f"\033[{r + 1};{c + 1}H")
                out.append(style_esc(cell.style.fg, cell.style.bg, sk))
                out.append(cell.char)

        cursor = self._cursor_esc()
        if out or cursor != self._last_cursor_esc:
            out.append(cursor)
            sys.stdout.write("".join(out))
            sys.stdout.flush()
            self._last_cursor_esc = cursor

    # ── hit testing ───────────────────────────────────────────────────────────

    def _hit_widget(self, widget, col, row):
        """Deepest focusable descendant of `widget` (children first) at (col, row)."""
        if hasattr(widget, "children"):
            for child in widget.children:
                result = self._hit_widget(child, col, row)
                if result:
                    return result
        if widget.focusable and widget.contains(col, row):
            return widget
        return None

    def _hit_test(self, col: int, row: int):
        """Return the topmost focusable base widget whose box contains (col, row)."""
        for widget in reversed(self.widgets):
            result = self._hit_widget(widget, col, row)
            if result:
                return result
        return None

    def quit(self):
        self._should_quit = True

    def run(self):
        enter = (
            "\033[?1049h\033[2J\033[H\033[?25l\033[?1000h\033[?1002h\033[?1006h\033[?2004h\033[>4;1m"
            if self.full
            else "\033[2J\033[H\033[?25l\033[?1000h\033[?1002h\033[?1006h\033[?2004h\033[>4;1m"
        )
        exit_ = (
            "\033[>4;0m\033[?2004l\033[?1006l\033[?1002l\033[?1000l\033[?25h\033[?1049l"
            if self.full
            else "\033[>4;0m\033[?2004l\033[?1006l\033[?1000l\033[?25h"
        )
        sys.stdout.write(enter)
        sys.stdout.flush()
        raw_state = enable_raw()
        try:
            while not self._should_quit:
                if self._check_resize():
                    pass  # buffer already rebuilt; fall through to render
                self.render()
                last_blink = time.monotonic()

                last_tick = time.monotonic()
                while not kbhit():
                    now = time.monotonic()
                    if self._drain_workers():
                        self.render()
                        last_blink = last_tick = now
                    elif self._check_resize():
                        self.render()
                        last_blink = last_tick = now
                    elif now - last_blink >= self.BLINK_INTERVAL:
                        self._cursor_on = not self._cursor_on
                        focused = self.focused
                        # For terminal-native cursors (vertical/block) the cursor
                        # is not in the cell buffer — just resend the cursor escape.
                        if (
                            focused is not None
                            and getattr(focused, "cursor", False)
                            and getattr(focused, "cursor_style", None)
                            in ("vertical", "block")
                        ):
                            esc = self._cursor_esc()
                            if esc != self._last_cursor_esc:
                                sys.stdout.write(esc)
                                sys.stdout.flush()
                                self._last_cursor_esc = esc
                        else:
                            self.render()
                            last_tick = now
                        last_blink = now
                    elif self.tick_interval and now - last_tick >= self.tick_interval:
                        self.render()
                        last_tick = now
                    # Block until input arrives or the next scheduled wake, rather
                    # than busy-spinning. Cap at _IDLE_POLL so resize and worker
                    # results are still noticed promptly.
                    now = time.monotonic()
                    waits = [_IDLE_POLL, self.BLINK_INTERVAL - (now - last_blink)]
                    if self.tick_interval:
                        waits.append(self.tick_interval - (now - last_tick))
                    wait_input(max(0.0, min(waits)))

                self._cursor_on = True
                key = read_key()
                if not key:  # None or "" from focus/resize console events
                    continue
                if isinstance(key, MouseClick):
                    modal = self._topmost_modal()
                    if modal is not None:
                        w = modal.widget
                        # Overlays are screen-fixed, so no scroll offset here.
                        inside = w.contains(key.col, key.row)
                        if not inside:
                            if modal.close_on_click_outside:
                                self.close_overlay(w)
                            continue  # clicks outside a modal are swallowed
                        target = self._hit_widget(w, key.col, key.row)
                        if target is not None:
                            self.focused = self._first_focusable(target) or target
                            if hasattr(target, "on_mouse_click"):
                                target.on_mouse_click(key.col, key.row)
                        continue
                    target = self._hit_test(key.col, key.row + self.scroll_y)
                    if target is not None:
                        # Clicking a container dives to its first child, matching Tab.
                        self.focused = self._first_focusable(target) or target
                        if hasattr(target, "on_mouse_click"):
                            target.on_mouse_click(key.col, key.row + self.scroll_y)
                    continue
                if isinstance(key, MouseDrag):
                    scroll = 0 if self._topmost_modal() else self.scroll_y
                    if self.focused and hasattr(self.focused, "on_mouse_drag"):
                        self.focused.on_mouse_drag(key.col, key.row + scroll)
                    continue
                modal = self._topmost_modal()
                if modal is not None:
                    # A modal captures all keys: no global handlers, no scroll.
                    if key == Key.ESC and modal.close_on_escape:
                        self.close_overlay(modal.widget)
                    elif key == Key.TAB:
                        self._cycle_focus(1)
                    elif key == Key.SHIFT_TAB:
                        self._cycle_focus(-1)
                    elif key == Key.CTRL_C and not (
                        self.focused and getattr(self.focused, "cursor", False)
                    ):
                        self.quit()
                    elif self.focused:
                        self.focused.on_key(key)
                    continue
                if key == Key.CTRL_C:
                    # Text inputs (cursor=True) handle Ctrl+C for copy; everything
                    # else treats it as quit.
                    if self.focused and getattr(self.focused, "cursor", False):
                        self.focused.on_key(key)
                    else:
                        self.quit()
                elif key in (Key.SCROLL_UP, Key.PAGE_UP, Key.CTRL_UP):
                    self._scroll(-3)
                elif key in (Key.SCROLL_DOWN, Key.PAGE_DOWN, Key.CTRL_DOWN):
                    self._scroll(3)
                elif key == Key.TAB:
                    self._cycle_focus(1)
                elif key == Key.SHIFT_TAB:
                    self._cycle_focus(-1)
                elif key in self._key_handlers:
                    result = self._key_handlers[key]()
                    if result == "quit" or self._should_quit:
                        break
                elif self.focused:
                    self.focused.on_key(key)
        except KeyboardInterrupt:
            pass
        finally:
            restore(raw_state)
            sys.stdout.write(exit_)
            sys.stdout.flush()
            # Warn after the screen is restored so it lands in normal scrollback.
            _maybe_warn_rich()
