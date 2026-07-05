import os
import sys
import threading
import time
from collections import deque

from cozy_tui._console import enable_raw, restore, wait_input
from cozy_tui._dock import SIDES, dock_layout
from cozy_tui._width import char_width
from cozy_tui.ansi import style_esc
from cozy_tui.events import (
    Key,
    MouseClick,
    MouseDrag,
    MouseMove,
    MouseRelease,
    kbhit,
    read_key,
)
from cozy_tui.style import Cell, Style

# Sentinel stored in _prev_cells to mark a cell that has never been rendered.
# Must not equal any valid (char, fg, bg, styles) tuple.
_UNSET = object()

# Longest the idle loop will block before re-checking terminal size / worker
# results, even when nothing else is due. Small enough to feel responsive,
# large enough that an idle app isn't busy-spinning.
_IDLE_POLL = 0.1


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
    # Two clicks on the same widget within this window count as a double-click.
    DOUBLE_CLICK_INTERVAL = 0.4

    def __init__(
        self,
        style: Style = Style(bg="black", fg="white"),
        size=None,
        full=True,
        title: str = "Cozy TUI App",
    ):
        self.style = style
        self.full = full
        # Whether any-motion tracking (?1003h, needed for hover/MouseMove) is
        # currently enabled at the terminal. Driven by per-widget mouse_moves:
        # the App turns it on when a live widget wants motion and never floods
        # the input stream otherwise. _running gates the live upgrade to when
        # the loop owns the terminal.
        self._motion_on = False
        self._running = False
        self.scroll_y = 0
        self._content_rows = 0

        self._init_size(size)

        self.widgets = []
        self.focused = None
        self._key_handlers = {}
        # Optional global mouse hook (see on_mouse); called with the raw event
        # before per-widget dispatch and may consume it by returning True.
        self._mouse_handler = None
        # Optional global right-click hook (see on_right_click); fired with
        # (col, row, widget_under_cursor) and may consume by returning True.
        self._right_click_handler = None
        # Last click for double-click detection: (monotonic time, target, btn).
        self._last_click = (0.0, None, None)
        # Widget the cursor is currently over, for enter/leave (mouse_moves).
        self._hovered = None
        # Bindings registered with a description, for the Bindings("auto") legend.
        # key -> (description, section); ordered by first registration.
        self._bindings: dict = {}
        self._bindings_version = 0
        self._cursor_on = True
        self._last_cursor_esc = None  # track last-emitted cursor state
        self._should_quit = False
        self.tick_interval: float | None = None  # set to e.g. 0.05 for animations
        # Frame interval requested by animating widgets during draw (e.g.
        # AnimatedLabel). Recomputed every render so animations self-drive the
        # loop without the app having to set tick_interval.
        self._anim_interval: float | None = None
        # Results from background workers, delivered to the main thread by the
        # event loop so callbacks never touch the UI from another thread.
        self._worker_results: deque = deque()
        # Overlay/z-layer stack drawn above the base widgets (last == topmost).
        self._overlays: list[_Overlay] = []
        # write() honours scroll_y normally; overlays are screen-fixed, so it is
        # flipped off while they draw.
        self._scroll_active = True
        raw_bg = self.style.raw_bg
        self._backdrop_style = Style(fg="bright_black", bg=raw_bg)
        self.title = title

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
        self._ensure_motion_mode()

    # ── mouse-motion tracking ─────────────────────────────────────────────────

    @staticmethod
    def _subtree_wants_motion(widget) -> bool:
        if getattr(widget, "mouse_moves", False):
            return True
        return any(
            App._subtree_wants_motion(c) for c in getattr(widget, "children", ())
        )

    def _wants_motion(self) -> bool:
        """True if any live widget (base or overlay) opted into mouse motion."""
        if any(self._subtree_wants_motion(w) for w in self.widgets):
            return True
        return any(self._subtree_wants_motion(e.widget) for e in self._overlays)

    def _ensure_motion_mode(self) -> None:
        """Upgrade the terminal to any-motion tracking (?1003h) the moment a
        widget that wants hover becomes live. Only ever upgrades from the
        drag-only ?1002h baseline — never downgrades — which keeps it flicker-
        free and cheap to call on every add()/open_overlay()."""
        if self._running and not self._motion_on and self._wants_motion():
            sys.stdout.write("\033[?1002l\033[?1003h")
            sys.stdout.flush()
            self._motion_on = True

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
        self._ensure_motion_mode()  # an overlay (e.g. a menu) may want hover
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

        dialog = PromptDialog(
            title, initial, on_submit=_submit, width=width, style=self.style
        )
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

    def on_key(self, key, handler, *, description=None, section=None):
        """Register a global key handler. Provide a ``description`` (and optional
        ``section``) to have it appear in a ``Bindings("auto")`` legend; without
        one the binding still works but is omitted from the legend."""
        self._key_handlers[key] = handler
        if description is not None:
            self._bindings[key] = (description, section)
            self._bindings_version += 1

    def on_mouse(self, handler):
        """Register a global mouse hook. ``handler(event)`` is called for every
        mouse event (``MouseClick``, ``MouseDrag``, ``MouseRelease``,
        ``MouseMove``) before it is dispatched to a widget, with coordinates
        already adjusted for scrolling. Return ``True`` to consume the event and
        skip the default per-widget dispatch."""
        self._mouse_handler = handler

    def on_right_click(self, handler):
        """Register a global right-click hook. ``handler(col, row, widget)`` is
        called when the right mouse button is pressed, with the focusable widget
        under the cursor (or ``None`` over empty space). Return ``True`` to
        consume it. A right-click never moves focus or activates a widget — this
        hook is the intended way to pop up a ``RightClickMenu``."""
        self._right_click_handler = handler

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

    def request_frame(self, interval: float) -> None:
        """Ask the event loop to redraw again after ``interval`` seconds. Called
        by animating widgets from their ``draw()`` so they keep moving without
        the app setting ``tick_interval``. The smallest request for the frame
        wins; it's cleared each render, so animation stops when nothing asks."""
        if interval and interval > 0:
            if self._anim_interval is None or interval < self._anim_interval:
                self._anim_interval = interval

    def _compose(self):
        """Run the draw pass into the cell buffer without emitting to the
        terminal. Shared by render() and snapshot()."""
        self._anim_interval = None  # widgets re-request during draw() below
        self.clear()
        self._apply_docks()
        for widget in self.widgets:
            widget.draw(self)
        self._draw_overlays()

    def snapshot(self) -> str:
        """Compose the current UI into a plain string — one line per row, with
        trailing blanks stripped — without touching the terminal. Intended for
        headless testing of app layouts (build the UI, assert on snapshot())."""
        self._compose()
        return "\n".join(
            "".join(cell.char for cell in row).rstrip() for row in self.buffer
        )

    def render(self):
        self._compose()

        # Safety net: a hover widget may have been added to a container (whose
        # add() the App can't intercept) or swapped in with a new page. Re-check
        # once per frame until motion is on; the guard makes this O(1) after the
        # first hover widget appears.
        if not self._motion_on:
            self._ensure_motion_mode()

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
        # Join with CRLF, not bare LF: POSIX raw mode (tty.setraw) disables OPOST,
        # so a lone "\n" moves down without returning to column 0 — which would
        # stair-step the whole screen. The explicit "\r" is a no-op on Windows.
        sys.stdout.write("\033[H" + "\r\n".join(lines) + cursor)
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

    def set_title(self, title: str):
        """Set the terminal tab/window title. Emits the OSC 0 sequence
        immediately so it takes effect mid-run, not just at startup."""
        self.title = title
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()

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

    # ── mouse dispatch ──────────────────────────────────────────────────────────

    def _mouse_target(self, col, row, modal):
        """Focusable widget under (col, row), confined to a modal overlay's
        subtree when one is open (or None when the point misses it)."""
        if modal is not None:
            if not modal.widget.contains(col, row):
                return None
            return self._hit_widget(modal.widget, col, row)
        return self._hit_test(col, row)

    def _dispatch_mouse(self, event):
        """Route a mouse event to the global hook then the widget under it.
        Coordinates are adjusted for scroll (overlays are screen-fixed) before
        either sees them."""
        modal = self._topmost_modal()
        event.row += 0 if modal else self.scroll_y
        if self._mouse_handler is not None and self._mouse_handler(event):
            return  # consumed by the global hook
        if isinstance(event, MouseClick):
            self._dispatch_click(event, modal)
        elif isinstance(event, MouseDrag):
            if self.focused is not None:
                self.focused.on_mouse_drag(event.col, event.row)
        elif isinstance(event, MouseRelease):
            if self.focused is not None:
                self.focused.on_mouse_release(event.col, event.row)
        elif isinstance(event, MouseMove):
            target = self._mouse_target(event.col, event.row, modal)
            # Only widgets that opted into motion receive hover/enter/leave.
            if target is not None and not target.mouse_moves:
                target = None
            if target is not self._hovered:
                if self._hovered is not None:
                    self._hovered.on_mouse_leave()
                self._hovered = target
                if target is not None:
                    target.on_mouse_enter()
            if target is not None:
                target.on_mouse_move(event.col, event.row)

    def _dispatch_click(self, event, modal):
        """Focus the clicked widget and fire click or double-click."""
        if modal is not None and not modal.widget.contains(event.col, event.row):
            if modal.close_on_click_outside:
                self.close_overlay(modal.widget)
            return  # clicks outside a modal are swallowed
        target = self._mouse_target(event.col, event.row, modal)
        if event.btn == 2:
            # Right-click takes its own path: it never steals focus or activates
            # the widget. The global hook (over empty space too) is the way to
            # pop up a context menu; per-widget on_mouse_right_click still fires.
            self._dispatch_right_click(event.col, event.row, target, modal)
            return
        if target is None:
            return
        # Clicking a container dives to its first child, matching Tab.
        self.focused = self._first_focusable(target) or target
        now = time.monotonic()
        last_t, last_target, last_btn = self._last_click
        double = (
            target is last_target
            and event.btn == last_btn
            and now - last_t <= self.DOUBLE_CLICK_INTERVAL
        )
        if double:
            target.on_mouse_double_click(event.col, event.row)
            self._last_click = (0.0, None, None)  # reset so a 3rd click isn't a 2nd
        else:
            target.on_mouse_click(event.col, event.row)
            self._last_click = (now, target, event.btn)

    def _dispatch_right_click(self, col, row, target, modal):
        """Fire the global right-click hook (only when no modal is up, so a menu
        doesn't retrigger itself) then the widget's own right-click handler."""
        if modal is None and self._right_click_handler is not None:
            if self._right_click_handler(col, row, target):
                return
        if target is not None:
            target.on_mouse_right_click(col, row)

    def quit(self):
        self._should_quit = True

    def _setup_sequences(self) -> tuple[str, str]:
        """Build the (enter, exit) VT escape sequences for the run loop.

        ``?7l`` disables autowrap (DECAWM). Without it, writing the bottom-right
        cell makes VTE-based terminals (gnome-terminal, Konsole) scroll the whole
        screen up, duplicating the top row; Windows Terminal defers the wrap so
        the bug stays hidden there. Every full-screen TUI turns this off (curses,
        Textual do too); ``?7h`` restores it on exit.
        """
        # 1003 = any-motion tracking (needed for hover/MouseMove); 1002 =
        # button-event tracking (motion only while a button is held, i.e. drag).
        # Start in 1003 only if a widget already wants hover; otherwise stay on
        # the cheap 1002 baseline and let _ensure_motion_mode() upgrade later.
        self._motion_on = self._wants_motion()
        motion = "1003" if self._motion_on else "1002"
        mouse_on = f"\033[?1000h\033[?{motion}h\033[?1006h"
        # Disable both motion modes on exit regardless of which we ended on (a
        # dynamic upgrade may have switched us to 1003 after setup).
        mouse_off = "\033[?1006l\033[?1003l\033[?1002l\033[?1000l"
        enter = (
            f"\033[?1049h\033[2J\033[H\033[?25l\033[?7l{mouse_on}\033[?2004h\033[>4;1m"
            if self.full
            else f"\033[2J\033[H\033[?25l\033[?7l{mouse_on}\033[?2004h\033[>4;1m"
        )
        exit_ = (
            f"\033[>4;0m\033[?2004l{mouse_off}\033[?7h\033[?25h\033[?1049l"
            if self.full
            else f"\033[>4;0m\033[?2004l{mouse_off}\033[?7h\033[?25h"
        )
        return enter, exit_

    def run(self):
        enter, exit_ = self._setup_sequences()

        self.set_title(self.title)  # emit OSC 0 terminal tab title

        sys.stdout.write(enter)
        sys.stdout.flush()
        raw_state = enable_raw()
        self._running = True
        try:
            while not self._should_quit:
                if self._check_resize():
                    pass  # buffer already rebuilt; fall through to render
                self.render()
                last_blink = time.monotonic()

                last_tick = time.monotonic()
                while not kbhit():
                    now = time.monotonic()
                    # Effective tick = the app's tick_interval and/or the fastest
                    # frame requested by an animating widget on the last render.
                    tick = self.tick_interval
                    if self._anim_interval is not None:
                        tick = (
                            self._anim_interval
                            if tick is None
                            else min(tick, self._anim_interval)
                        )
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
                    elif tick and now - last_tick >= tick:
                        self.render()
                        last_tick = now
                    # Block until input arrives or the next scheduled wake, rather
                    # than busy-spinning. Cap at _IDLE_POLL so resize and worker
                    # results are still noticed promptly.
                    now = time.monotonic()
                    waits = [_IDLE_POLL, self.BLINK_INTERVAL - (now - last_blink)]
                    if tick:
                        waits.append(tick - (now - last_tick))
                    wait_input(max(0.0, min(waits)))

                self._cursor_on = True
                key = read_key()
                if not key:  # None or "" from focus/resize console events
                    continue
                if isinstance(key, (MouseClick, MouseDrag, MouseRelease, MouseMove)):
                    self._dispatch_mouse(key)
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
            self._running = False
            restore(raw_state)
            sys.stdout.write(exit_)
            sys.stdout.flush()
