import atexit
import os
import signal
import sys
import threading
import time
from collections import deque

from cozy_tui._console import enable_raw, flush_input, restore, wait_input
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

# Bounded so a long-running App(debug=True) doesn't leak memory from app.debug().
_DEBUG_LOG_MAXLEN = 500


class _Timer:
    """A scheduled callback fired by the event loop on the main thread. `interval`
    is ``None`` for a one-shot (``app.after``) or the repeat period (``app.every``);
    `deadline` is the next ``time.monotonic()`` at which it should fire."""

    __slots__ = ("deadline", "callback", "interval", "alive")

    def __init__(self, deadline, callback, interval):
        self.deadline = deadline
        self.callback = callback
        self.interval = interval
        self.alive = True


class _Overlay:
    """A widget layered above the base UI. `modal` confines keyboard/mouse input
    to it (and, with `dim`, grays the background); a non-modal overlay is purely
    visual (e.g. a tooltip, an actionable Toast's buttons). `prev_focus` is
    restored when the overlay closes."""

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
    # Two clicks on the same widget within this window count as a double click.
    DOUBLE_CLICK_INTERVAL = 0.4

    def __init__(
        self,
        style: Style | None = None,
        size=None,
        full=True,
        title: str = "Cozy TUI App",
        catch_errors: bool = True,
        debug: bool | None = None,
        debug_log_path: str | None = None,
        default_logs: bool = True,
    ):
        if style is not None:
            self.style = style
        else:
            # Derive a *copy* of the active theme's base style (cozy_tui.theme),
            # not the same instance -- otherwise every App() built with no
            # explicit style= would share one mutable Style, and mutating one
            # app's .style would leak into every other such app.
            from cozy_tui.theme import get_theme

            t_style = get_theme().style
            self.style = Style(fg=t_style.fg, bg=t_style.raw_bg, styles=t_style.styles)
        self.full = full
        # None (the default) defers to COZY_TUI_DEBUG=1, set by `cozy-tui run
        # --debug script.py` — so a script needs no code change to opt in from
        # the CLI. An explicit True/False here always wins over the env var.
        if debug is None:
            debug = os.environ.get("COZY_TUI_DEBUG") == "1"
        # If True (the default), an unhandled exception from run() is shown as
        # a full-screen crash view (cozy_tui.crash_screen.show_traceback)
        # instead of propagating — after the terminal has been cleanly
        # restored either way. Pass False for a script/test that wants run()
        # to raise normally, or that can't offer a real interactive terminal
        # for the crash screen to block on (e.g. running under CI/headless).
        self.catch_errors = catch_errors
        # app.debug(...) is safe to call while the raw-mode/alt-screen loop is
        # running (unlike print(), which would corrupt the display). Off by
        # default: no buffer is even allocated unless debug=True, so apps that
        # never use it pay nothing. View it with the F12 pane (bound below,
        # only when debug=True) or tail `debug_log_path` from another terminal.
        self._debug_log = deque(maxlen=_DEBUG_LOG_MAXLEN) if debug else None
        self._debug_seq = 0
        # Auto-logs focus changes, key presses, and mouse clicks/drags
        # via app.debug() — meaningless (and never checked) unless debug=True
        # too. Pass default_logs=False to keep app.debug() for your own
        # messages only.
        self._default_logs = debug and default_logs
        self._debug_file = None
        if debug and debug_log_path:
            try:
                self._debug_file = open(debug_log_path, "a", encoding="utf-8")
            except OSError:
                self._debug_file = None
        # F12 Cozy DevTools panel state (see _devtools.py). _devtools_active
        # gates both the Elements-tab mouse takeover in _dispatch_mouse and
        # the Esc-to-unfreeze branch in _dispatch_input; _devtools_tabs is
        # the panel's inner Tabs instance, checked for
        # `selected_title == "Elements"`. _selection_seq is bumped whenever
        # the selected widget/frozen-state changes so the Elements tab only
        # rebuilds its rows on an actual change, like _LiveLog's _debug_seq.
        self._devtools_active = False
        self._devtools_panel = None
        self._devtools_tabs = None
        # The _AppContentPane wrapping the app's own pre-existing top-level
        # widgets while DevTools is open (see toggle_devtools) -- add()
        # redirects into its .children instead of self.widgets whenever this
        # is set, so anything the app adds mid-session still lands in the
        # right place instead of becoming an orphaned second top-level item.
        self._devtools_content_pane = None
        self._devtools_splitter = None
        self._devtools_prev_focus = None
        self._selected_widget = None
        self._selection_frozen = False
        self._selection_seq = 0
        # Timings are only ever computed when debug=True (render()/_compose()
        # check self._debug_log is not None before touching perf_counter at
        # all), so a non-debug app pays nothing beyond these zero-cost
        # scalars. Read by the DevTools panel's Performance tab.
        self._last_frame_ms = 0.0
        self._last_render_ms = 0.0
        self._debug_layout_ms = 0.0
        self._last_mouse_pos = (0, 0)
        # Rolling render() timestamps for FPS (see _current_fps) -- a real
        # deque, so (like _debug_log) only allocated when debug=True.
        self._frame_times: deque = deque(maxlen=30) if debug else None
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
        # Scheduled callbacks (app.after / app.every), fired from the loop.
        self._timers: list[_Timer] = []
        # Active toast notifications, drawn stacked in a screen corner.
        self._toasts: list = []
        # Overlay/z-layer stack drawn above the base widgets (last == topmost).
        self._overlays: list[_Overlay] = []
        # write() honours scroll_y normally; overlays are screen-fixed, so it is
        # flipped off while they draw.
        self._scroll_active = True
        # Clip-rectangle stack (in abs content coords): write() drops cells that
        # fall outside the top rect. ScrollView pushes its viewport onto it.
        self._clip_stack: list = []
        self.title = title
        if debug:
            self.on_key(
                Key.F12,
                self.toggle_devtools,
                description="Toggle Cozy DevTools",
                section="Debug",
            )
        self.on_key(
            Key.CTRL_T,
            self.open_theme_palette,
            description="Change theme",
            section="App",
        )
        # name -> Command, insertion order preserved (a Python dict); built-ins
        # go first, so they lead the palette unless a user overrides one by
        # re-registering the same name.
        self._commands: dict = {}
        self.register_command("Quit", self.quit, description="Quit the application")
        self.register_command(
            "Change Theme",
            self.open_theme_palette,
            description="Change the current color theme",
        )
        self.register_command(
            "Keys",
            self._show_keys,
            description="Show a summary of available keybindings",
        )
        if debug:
            self.register_command(
                "Toggle DevTools",
                self.toggle_devtools,
                description="Open or close Cozy DevTools",
            )
        self.on_key(
            Key.CTRL_P,
            self.open_command_palette,
            description="Command palette",
            section="App",
        )

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
        self._alloc_buffers()

    def _alloc_buffers(self):
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
        self._alloc_buffers()
        max_scroll = max(0, self._content_rows - self.rows)
        self.scroll_y = min(self.scroll_y, max_scroll)
        return True

    def _scroll(self, delta):
        max_scroll = max(0, self._content_rows - self.rows)
        self.scroll_y = max(0, min(self.scroll_y + delta, max_scroll))

    def add(self, widget):
        # While DevTools is open, self.widgets holds only the wrapping
        # Splitter (see toggle_devtools) -- redirect into the wrapped app
        # content instead, so a widget added mid-session (e.g. from a timer
        # or worker callback) lands alongside the rest of the real app
        # instead of becoming an orphaned, undocked second top-level item.
        target = (
            self._devtools_content_pane.children
            if self._devtools_content_pane is not None
            else self.widgets
        )
        target.append(widget)
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
        drag-only ?1002h baseline — never downgrades — which keeps it flicker-free
        and cheap to call on every add()/open_overlay()."""
        if self._running and not self._motion_on and self._wants_motion():
            # Re-assert SGR extended coordinates (?1006h) after switching tracking
            # modes: some terminals (WezTerm) otherwise revert to the legacy X10
            # encoding, whose high bytes get mangled by the UTF-8 input decoder —
            # breaking clicks/hover and leaving X10 motion reports on exit.
            sys.stdout.write("\033[?1002l\033[?1003h\033[?1006h")
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
        (and, with `dim`, grays the background); a **non-modal** overlay is purely
        visual, e.g. a tooltip or an actionable Toast's buttons. `center`
        re-centres the widget on screen every frame (use a `Box` for a
        dialog). `close_on_escape` / `close_on_click_outside` give light
        dismissal. Whatever was focused before a modal overlay opens is
        restored when it closes. Overlays are screen-fixed (ignore
        scrolling). Returns `widget`.
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
            self._set_focused(self._first_focusable(widget))
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
        self._set_focused(entry.prev_focus)
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
            dialog, close_on_click_outside=close_on_click_outside, on_close=_on_close
        )
        return dialog

    def confirm(
        self,
        message,
        *,
        on_yes=None,
        on_no=None,
        yes_label="Yes",
        no_label="No",
        default=True,
        width=40,
        close_on_click_outside=True,
    ):
        """Open a Yes/No confirmation modal. Left/Right (or Tab) move between
        the buttons, Enter picks the highlighted one, Y/N pick directly, a
        click picks whichever button it lands on. ``on_yes()``/``on_no()``
        (each optional, no arguments) fire when the matching choice is made;
        cancelling -- Esc or a click outside -- calls ``on_no()`` too, since
        "didn't confirm" should behave like "said no" for anything gated
        behind a confirmation. Returns the ``ConfirmDialog`` widget."""
        from cozy_tui.widgets.selection.confirm_dialog import ConfirmDialog

        state = {"chosen": False}

        def _choose(yes):
            state["chosen"] = True
            self.close_overlay(dialog)
            if yes:
                if on_yes is not None:
                    on_yes()
            elif on_no is not None:
                on_no()

        def _on_close(_widget):
            if not state["chosen"] and on_no is not None:
                on_no()

        dialog = ConfirmDialog(
            message,
            yes_label=yes_label,
            no_label=no_label,
            default=default,
            on_choose=_choose,
            width=width,
            style=self.style,
        )
        self.open_overlay(
            dialog, close_on_click_outside=close_on_click_outside, on_close=_on_close
        )
        return dialog

    def pick_file(
        self,
        start_dir=None,
        *,
        mode="file",
        extensions=None,
        on_select=None,
        on_cancel=None,
        width=60,
        height=10,
        close_on_click_outside=True,
    ):
        """Open a modal file/directory picker rooted at ``start_dir``
        (defaults to the current working directory). ``mode="file"``
        (default) lets you browse into directories and pick a file;
        ``mode="directory"`` shows a "Select this folder" entry instead of
        listing files, for picking a directory itself. ``extensions`` (e.g.
        ``(".py", ".md")``) restricts which files are shown in file mode.
        ``on_select(path)`` fires with a ``pathlib.Path`` when something is
        chosen and closes the picker; cancelling -- Esc or a click outside --
        calls ``on_cancel()``. Returns the ``FilePicker`` widget."""
        from cozy_tui.widgets.selection.file_picker import FilePicker

        state = {"picked": False}

        def _choose(path):
            state["picked"] = True
            self.close_overlay(picker)
            if on_select is not None:
                on_select(path)

        def _on_close(_widget):
            if not state["picked"] and on_cancel is not None:
                on_cancel()

        picker = FilePicker(
            start_dir,
            mode=mode,
            extensions=extensions,
            on_select=_choose,
            width=width,
            height=height,
            style=self.style,
        )
        self.open_overlay(
            picker, close_on_click_outside=close_on_click_outside, on_close=_on_close
        )
        return picker

    def toast(
        self,
        message,
        *,
        level="info",
        duration=3.0,
        icon=None,
        corner="bottom-right",
        actions=None,
    ):
        """Pop a transient notification that auto-dismisses after ``duration``
        seconds. ``level`` is ``"info"``/``"success"``/``"warning"``/``"error"``
        (sets color + default icon). Stacks with other toasts in ``corner``.

        ``actions`` is an optional list of ``(label, callback)`` pairs
        rendered as clickable ``[ Label ]`` buttons under the message, e.g.
        ``[("Undo", restore_item), ("Dismiss", None)]`` -- ``callback=None``
        means the action just closes the toast. Clicking one fires its
        callback (if given) and dismisses this toast; it never moves
        ``app.focused``, so it can't steal focus from whatever you were
        actually working in. While ``actions`` is given, hovering the toast
        pauses its auto-dismiss timer (restarting it in full once the mouse
        leaves) so reaching for a button doesn't get the toast pulled out
        from under the cursor mid-click.

        Returns the :class:`Toast` widget."""
        from cozy_tui.widgets.display.toast import Toast

        toast = Toast(message, level=level, icon=icon, corner=corner, actions=actions)
        self._toasts.append(toast)
        self.open_overlay(
            toast, modal=False, dim=False, center=False, close_on_escape=False
        )

        if actions:

            def _on_action(index):
                _label, callback = actions[index]
                if callback is not None:
                    callback()
                self._dismiss_toast(toast)

            toast.on_action(_on_action)

        state = {"timer": None}

        def _arm():
            if duration and duration > 0:
                state["timer"] = self.after(
                    duration, lambda: self._dismiss_toast(toast)
                )

        if actions:
            toast.on_enter(lambda _t: self.cancel(state["timer"]))
            toast.on_leave(lambda _t: _arm())
        _arm()
        return toast

    def _dismiss_toast(self, toast):
        if toast in self._toasts:
            self._toasts.remove(toast)
            self.close_overlay(toast)

    def set_tooltip(self, widget, text: str, *, delay: float = 0.4) -> None:
        """Show `text` in a small floating bubble anchored just below `widget`
        while the mouse hovers over it, after `delay` seconds (so a quick
        pass-through doesn't flash one), and hide it the instant the mouse
        leaves. Wires `widget.on_enter`/`on_leave` to do this -- which also
        opts `widget` into hover tracking, same as calling those yourself --
        so it replaces any enter/leave handler already registered on
        `widget` (each is a single callback slot, like `on_click`)."""
        state = {"timer": None, "tip": None}

        def _hide(_w=None) -> None:
            if state["timer"] is not None:
                self.cancel(state["timer"])
                state["timer"] = None
            if state["tip"] is not None:
                self.close_overlay(state["tip"])
                state["tip"] = None

        def _open() -> None:
            from cozy_tui.widgets.display.tooltip import Tooltip

            state["timer"] = None
            tip = Tooltip(
                widget, text
            )  # Tooltip's own default style (a high-contrast callout)
            state["tip"] = tip
            self.open_overlay(
                tip, modal=False, dim=False, center=False, close_on_escape=False
            )

        def _show(_w) -> None:
            _hide()  # defensive: shouldn't already be showing, but don't double-open
            state["timer"] = self.after(delay, _open)

        widget.on_enter(_show)
        widget.on_leave(_hide)

    def debug(self, *values, sep: str = " ") -> None:
        """Append a debug message — safe to call while the raw-mode/alt-screen
        loop is running, unlike ``print()``, which would corrupt the display.
        No-op unless the app was built with ``App(debug=True)``. View the log
        with the F12 pane, or read ``debug_log_path`` from another terminal if
        one was given."""
        if self._debug_log is None:
            return
        line = sep.join(str(v) for v in values)
        self._debug_log.append(line)
        self._debug_seq += 1
        if self._debug_file is not None:
            try:
                self._debug_file.write(line + "\n")
                self._debug_file.flush()
            except Exception:
                pass

    def toggle_devtools(self) -> None:
        """Open or close the F12 Cozy DevTools panel: Elements (follows the
        mouse -- see `_hit_any`, `_dispatch_mouse` -- and highlights
        whatever it's pointing at via `_devtools.draw_highlight`; a click
        freezes it on that widget without activating it, Esc while frozen
        resumes live tracking), Console (the live debug log), Performance
        (FPS/timings), and Tree (the live widget hierarchy -- clicking a
        node selects and highlights it, without leaving the Tree tab; switch
        to Elements yourself for the detail). A no-op if the app wasn't
        built with ``App(debug=True)``.

        Not an overlay -- a real docked pane, split from the app's own
        content by a draggable `Splitter` (drag the bar, or focus it and use
        Left/Right, exactly like any other `Splitter`), so the app visibly
        shrinks to share the screen instead of being covered. Bound to F12
        automatically when `debug=True`; call it yourself to trigger it from
        a menu item, button, or your own key binding instead."""
        if self._debug_log is None:
            return
        if self._devtools_active:
            self._close_devtools()
            return
        from cozy_tui._devtools import DevToolsPanel, _AppContentPane
        from cozy_tui.widgets import Splitter

        self._devtools_active = True
        self._selection_frozen = False
        self._selected_widget = None
        self._selection_seq += 1
        self._devtools_prev_focus = self.focused

        content_pane = _AppContentPane(self.widgets)
        for widget in content_pane.children:
            widget.parent = content_pane

        panel = DevToolsPanel(self)
        self._devtools_panel = panel
        self._devtools_tabs = panel.tabs

        # first=app content (left), second=DevTools (right); ratio=0.62
        # gives the app the majority share by default -- drag from there.
        splitter = Splitter(0, 0, "10x10", content_pane, panel, ratio=0.62, min_size=20)
        self._devtools_splitter = splitter
        self.widgets = []
        self.dock(splitter, "fill")  # "fill", not a bare append: re-evaluated
        # every frame, so a terminal resize is tracked live. Set only *after*
        # dock()/add() has placed the splitter itself onto self.widgets --
        # add() redirects into this pane once it's set (see App.add()), and
        # the splitter must land as the sole top-level widget, not get
        # nested inside the very pane it's meant to wrap.
        self._devtools_content_pane = content_pane
        self.invalidate()

    def _close_devtools(self) -> None:
        content_pane = self._devtools_content_pane
        for widget in content_pane.children:
            widget.parent = None
        self.widgets = content_pane.children  # not the original snapshot --
        # anything add()-ed mid-session (redirected into this pane, see
        # App.add()) must not be lost when DevTools closes.
        self._set_focused(self._devtools_prev_focus)
        self._devtools_active = False
        self._devtools_panel = None
        self._devtools_tabs = None
        self._devtools_content_pane = None
        self._devtools_splitter = None
        self._devtools_prev_focus = None
        self._selection_frozen = False
        self._selected_widget = None
        self.invalidate()

    def _current_fps(self) -> float:
        """Rolling FPS over the last `_frame_times` (up to 30) render() calls.
        Reads 0 with fewer than 2 samples, and near-zero whenever the app is
        otherwise idle -- this engine renders on demand rather than on a
        fixed cadence (see run()'s loop, which blocks in wait_input() until
        something is actually due), so a low idle FPS is expected, not a
        stall. It climbs while something keeps the loop busy: an animation,
        the cursor blink, or the DevTools panel's own `request_frame`."""
        if not self._frame_times or len(self._frame_times) < 2:
            return 0.0
        span = self._frame_times[-1] - self._frame_times[0]
        if span <= 0:
            return 0.0
        return (len(self._frame_times) - 1) / span

    def _count_widgets(self) -> int:
        """Total live widget count: every base widget and overlay, descending
        into each container's `.children`. Feeds the DevTools Performance
        tab's "Widgets" figure."""

        def _count(widget) -> int:
            n = 1
            for child in getattr(widget, "children", None) or ():
                n += _count(child)
            return n

        total = sum(_count(w) for w in self.widgets)
        total += sum(_count(e.widget) for e in self._overlays)
        return total

    def cycle_theme(self) -> None:
        """Advance the process-wide active theme (`cozy_tui.theme`) to the next
        built-in mode, wrapping from the last back to the first, and repaint.
        Not bound by default (Ctrl+T opens `open_theme_palette` instead) --
        call this yourself, or register it on your own key, for a plain
        one-shot-per-press cycle instead of a searchable list. Widgets that
        share this app's `.style` object (rather than their own copy) pick up
        the new base colors on the next frame; a widget with its own style
        needs to opt in the same way `selection_style()` already does."""
        from cozy_tui.theme import Theme, get_theme

        modes = Theme.MODES
        current = get_theme().mode
        idx = modes.index(current) if current in modes else -1
        theme = Theme(mode=modes[(idx + 1) % len(modes)]).activate()
        self.style.fg = theme.style.fg
        self.style.bg = theme.style.bg  # already carries Style's "_bg" suffix
        self.invalidate()

    def open_theme_palette(
        self, *, width=36, height=8, close_on_click_outside=True
    ) -> None:
        """Open a searchable Ctrl+T palette -- type to filter, Up/Down to
        move, Enter or a click to pick, Esc/click-outside to cancel -- listing
        every built-in `cozy_tui.theme` mode. Picking one activates it,
        mutates this app's own `.style` in place, and repaints (same effect
        as `cycle_theme()`, just from a deliberate choice instead of a
        cycle). Call it yourself to trigger the same palette from a menu item
        or button."""
        from cozy_tui.theme import Theme, get_theme
        from cozy_tui.widgets.selection.theme_palette import ThemePalette

        def _pick(mode):
            theme = Theme(mode=mode).activate()
            self.style.fg = theme.style.fg
            self.style.bg = theme.style.bg  # already carries Style's "_bg" suffix
            self.invalidate()
            self.close_overlay(palette)

        palette = ThemePalette(
            Theme.MODES,
            current=get_theme().mode,
            on_select=_pick,
            width=width,
            height=height,
            style=self.style,
        )
        self.open_overlay(palette, close_on_click_outside=close_on_click_outside)

    def register_command(self, name: str, callback, *, description: str = "") -> None:
        """Register (or, re-using an existing `name`, override) an entry in
        the Ctrl+P command palette (`open_command_palette`). `callback` is
        invoked with no arguments when the command is picked, after the
        palette has already closed. `App` itself registers a few built-ins
        this way ("Quit", "Change Theme", "Keys", and -- only when
        `debug=True` -- "Toggle DevTools"), so overriding one of those names
        replaces it."""
        from cozy_tui.widgets.selection.command_palette import Command

        self._commands[name] = Command(name, callback, description=description)

    def open_command_palette(
        self, *, width=52, height=6, close_on_click_outside=True
    ) -> None:
        """Open a searchable Ctrl+P palette -- type to filter by name or
        description, Up/Down to move, Enter or a click to run the highlighted
        command, Esc/click-outside to cancel -- listing every command
        registered with `register_command` (including App's own built-ins).
        Call it yourself to trigger the same palette from a menu item or
        button."""
        from cozy_tui.widgets.selection.command_palette import CommandPalette

        def _run(command):
            self.close_overlay(palette)
            if command.callback is not None:
                command.callback()

        palette = CommandPalette(
            list(self._commands.values()),
            on_select=_run,
            width=width,
            height=height,
            style=self.style,
        )
        self.open_overlay(palette, close_on_click_outside=close_on_click_outside)

    def _show_keys(self) -> None:
        """Open the "Keys" command: a read-only Bindings("auto") legend of
        every currently-registered global key binding, as a dismissable
        modal overlay."""
        from cozy_tui.widgets.display.bindings import Bindings

        legend = Bindings(0, 0, self, title="Keys")
        self.open_overlay(legend, close_on_click_outside=True)

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
        """Gray every already-drawn cell (chars kept) as a scrim behind a modal."""
        # Recomputed from self.style every call (like every other raw_bg use in
        # this codebase) rather than cached, so the scrim tracks the active
        # theme's background even after a theme switch post-__init__.
        style = Style(fg="bright_black", bg=self.style.raw_bg)
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
        self._set_focused(widget)

    def _set_focused(self, widget) -> None:
        """The single place `self.focused` is assigned (besides the initial
        `None` in `__init__`), so default-logs has one hook instead of one
        per call site."""
        self.focused = widget
        if self._default_logs:
            self.debug(f"Focused on widget: {widget}")

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

    # ── timers ────────────────────────────────────────────────────────────────

    def after(self, delay, callback):
        """Call ``callback()`` once, ``delay`` seconds from now, on the main
        thread from the event loop. Returns a handle for :meth:`cancel`."""
        timer = _Timer(time.monotonic() + delay, callback, None)
        self._timers.append(timer)
        return timer

    def every(self, interval, callback):
        """Call ``callback()`` every ``interval`` seconds on the main thread until
        canceled. Returns a handle for :meth:`cancel`."""
        timer = _Timer(time.monotonic() + interval, callback, interval)
        self._timers.append(timer)
        return timer

    def cancel(self, timer):
        """Cancel a timer returned by :meth:`after` / :meth:`every`."""
        if timer is not None:
            timer.alive = False

    def _next_timer_deadline(self, now):
        """Seconds until the soonest live timer fires, or ``None`` if none."""
        deadlines = [t.deadline - now for t in self._timers if t.alive]
        return min(deadlines) if deadlines else None

    def _drain_timers(self, now):
        """Fire every timer whose deadline has passed; reschedule repeats and drop
        spent/canceled ones. Returns True if any fired (so the caller re-renders)."""
        fired = False
        for timer in list(self._timers):  # snapshot: callbacks may add timers
            if timer.alive and now >= timer.deadline:
                timer.callback()
                fired = True
                if timer.interval is not None:
                    # keep periodic timers on a fixed cadence, skipping missed slots
                    timer.deadline += timer.interval
                    if timer.deadline <= now:
                        timer.deadline = now + timer.interval
                else:
                    timer.alive = False
        if any(not t.alive for t in self._timers):
            self._timers = [t for t in self._timers if t.alive]
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
        self._set_focused(focusables[(idx + direction) % len(focusables)])

    def push_clip(self, x0, y0, x1, y1):
        """Confine subsequent ``write`` calls to the rectangle ``[x0, x1) ×
        [y0, y1)`` (abs content coords). Balance with :meth:`pop_clip`. Used by
        ScrollView to clip its content to the viewport."""
        self._clip_stack.append((x0, y0, x1, y1))

    def pop_clip(self):
        if self._clip_stack:
            self._clip_stack.pop()

    def write(self, x, y, text, style: Style):
        clip = self._clip_stack[-1] if self._clip_stack else None
        if clip is not None and not (clip[1] <= y < clip[3]):
            return  # whole row is outside the active clip rectangle
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
            if col >= 0 and (clip is None or clip[0] <= col < clip[2]):
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
        self._clip_stack.clear()  # defensive: no clip leaks across frames
        if self._debug_log is not None:
            self._debug_layout_ms = 0.0  # accumulated by Layout.draw() below
        self.clear()
        self._apply_docks()
        for widget in self.widgets:
            widget.draw(self)
        if self._devtools_active and self._selected_widget is not None:
            from cozy_tui._devtools import draw_highlight

            draw_highlight(self, self._selected_widget)
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
        if self._debug_log is None:
            self._compose()
        else:
            # Timed only under App(debug=True): feeds the DevTools
            # Performance tab's Frame/Render/FPS figures. "Frame" is the
            # wall-clock gap since the previous render() call started (i.e.
            # frame-to-frame cost, including idle time spent blocked in
            # wait_input()); "Render" is _compose() alone.
            frame_start = time.perf_counter()
            if self._frame_times:
                self._last_frame_ms = (frame_start - self._frame_times[-1]) * 1000
            self._compose()
            self._last_render_ms = (time.perf_counter() - frame_start) * 1000
            self._frame_times.append(frame_start)

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
        """Write only cells that changed since the last render, coalescing each
        span of consecutive changed cells into a single cursor move + a style
        escape per style change (rather than one per cell)."""
        out = []
        prev = self._prev_cells

        for r, row in enumerate(self.buffer):
            prev_row = prev[r]
            n = len(row)
            c = 0
            while c < n:
                cell = row[c]
                sk = cell.style.styles
                key = (cell.char, cell.style.fg, cell.style.bg, sk)
                if key == prev_row[c]:
                    c += 1
                    continue
                # start a run at column c: one cursor move for the whole span
                out.append(f"\033[{r + 1};{c + 1}H")
                cur_style = None
                while c < n:
                    cell = row[c]
                    sk = cell.style.styles
                    key = (cell.char, cell.style.fg, cell.style.bg, sk)
                    if key == prev_row[c]:
                        break  # run ends at the first unchanged cell
                    prev_row[c] = key
                    style_key = (cell.style.fg, cell.style.bg, sk)
                    if style_key != cur_style:
                        out.append(style_esc(cell.style.fg, cell.style.bg, sk))
                        cur_style = style_key
                    out.append(cell.char)
                    c += 1

        cursor = self._cursor_esc()
        if out or cursor != self._last_cursor_esc:
            body = "".join(out)
            if body:
                body += "\033[0m"  # reset after the runs; each run re-sets style
            sys.stdout.write(body + cursor)
            sys.stdout.flush()
            self._last_cursor_esc = cursor

    def set_title(self, title: str):
        """Set the terminal tab/window title. Emits the OSC 0 sequence
        immediately so it takes effect mid-run, not just at startup."""
        self.title = title
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()

    # ── hit testing ───────────────────────────────────────────────────────────

    def _hit_widget(self, widget, col, row, require_focusable=True):
        """Deepest descendant of `widget` (children first) at (col, row).
        `require_focusable=True` (the default, used by click/hover dispatch)
        only ever returns a `focusable` widget; `_hit_any` passes `False` so
        the F3 inspector can point at *any* widget -- a plain Label or
        decorative Box is worth inspecting even though it never receives
        input."""
        if hasattr(widget, "children"):
            # Reversed: later-added (visually topmost) children win, matching
            # both draw order and the top-level policy in _hit_test — otherwise
            # overlapping siblings route clicks to the bottom-most one.
            for child in reversed(widget.children):
                result = self._hit_widget(child, col, row, require_focusable)
                if result:
                    return result
        if (not require_focusable or widget.focusable) and widget.contains(col, row):
            return widget
        return None

    def _hit_test(self, col: int, row: int):
        """Return the topmost focusable base widget whose box contains (col, row)."""
        for widget in reversed(self.widgets):
            result = self._hit_widget(widget, col, row)
            if result:
                return result
        return None

    def _hit_any(self, col: int, row: int):
        """Return the topmost widget of *any* kind (focusable or not) whose
        box contains (col, row) -- overlays first (topmost z-layer), then
        base widgets, recursing through anything with `.children` (including
        the `Splitter`/`_AppContentPane` DevTools wraps the app in while
        open -- see `toggle_devtools`). Used only by the DevTools Elements
        tab (`toggle_devtools`, `_dispatch_mouse`); everything else keeps
        using `_hit_test`, which only ever targets something that can
        actually receive input.

        Never matches or recurses into `self._devtools_panel` itself --
        Elements doesn't inspect the DevTools panel's own chrome, whether
        that panel happens to be an overlay or (as it is now) a real widget
        nested inside the Splitter."""

        def _walk(widget):
            if widget is self._devtools_panel:
                return None
            if hasattr(widget, "children"):
                for child in reversed(widget.children):
                    result = _walk(child)
                    if result:
                        return result
            if widget.contains(col, row):
                return widget
            return None

        for entry in reversed(self._overlays):
            result = _walk(entry.widget)
            if result:
                return result
        for widget in reversed(self.widgets):
            result = _walk(widget)
            if result:
                return result
        return None

    def _hit_non_modal_overlay(self, col: int, row: int):
        """Topmost non-modal overlay widget (focusable or not) whose box
        contains (col, row), or `None`. Only ever called when no modal is
        open (a modal already captures all mouse input exclusively, see
        `_dispatch_click`) -- so every overlay here genuinely is non-modal.

        Non-modal overlays (`Toast`, `Tooltip`) are otherwise mouse-
        transparent: `_mouse_target`/`_hit_test` only ever look at the base
        UI unless a modal is open. This is the one exception, giving an
        overlay that wants clicks/hover (an actionable `Toast`'s buttons) a
        first look, topmost z-layer first, before falling through to the
        base UI -- see `_dispatch_mouse`. (DevTools isn't an overlay at all
        -- see `App.toggle_devtools` -- so it never registers here; its own
        tab bar/Tree are real focusable widgets reached by the ordinary
        `_hit_test()` path below instead.)"""
        for entry in reversed(self._overlays):
            result = self._hit_widget(entry.widget, col, row, require_focusable=False)
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

    def _dispatch_input(self, key) -> None:
        """Route one parsed input event through App's normal input semantics:
        mouse events to `_dispatch_mouse`, everything else (a `Key.*`
        constant, a plain character, or a `Paste`) through the modal /
        global-key-handler / focused-widget chain. `run()` calls this with
        whatever `read_key()` returned; it's also the extension point for a
        frontend with no real terminal underneath (see `_internal/ctui_web`)
        that already has a parsed event and wants the same routing `run()`
        gets, without going through `read_key()`/a terminal at all."""
        if isinstance(key, (MouseClick, MouseDrag, MouseRelease, MouseMove)):
            self._dispatch_mouse(key)
            return
        if self._default_logs and key not in (Key.SCROLL_UP, Key.SCROLL_DOWN):
            self.debug(f"Pressed on key: {key}")
        modal = self._topmost_modal()
        if modal is not None:
            # A modal captures all keys: no global handlers, no scroll --
            # except F12, which always reaches Cozy DevTools (a no-op if
            # debug=False) rather than being swallowed as a second "close
            # this modal" key. Otherwise F12 could never open DevTools while
            # any modal (there are many now: ConfirmDialog, FilePicker,
            # CommandPalette, ThemePalette, ...) happens to be open.
            if key == Key.F12:
                self.toggle_devtools()
            elif key == Key.ESC and modal.close_on_escape:
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
            return
        if self._devtools_active and key == Key.ESC and self._selection_frozen:
            # Resume live hover-tracking on the Elements tab; F12 (not Esc)
            # is the only way to close DevTools entirely -- a symmetric
            # open/close key.
            self._selection_frozen = False
            return
        if key == Key.CTRL_C:
            # Text inputs (cursor=True) handle Ctrl+C for copy; everything
            # else treats it as quit.
            if self.focused and getattr(self.focused, "cursor", False):
                self.focused.on_key(key)
            else:
                self.quit()
        elif key in (
            Key.SCROLL_UP,
            Key.SCROLL_DOWN,
            Key.PAGE_UP,
            Key.PAGE_DOWN,
            Key.CTRL_UP,
            Key.CTRL_DOWN,
        ):
            # A focused scrollable widget (ScrollView) consumes the wheel
            # / page keys; otherwise they scroll the whole base UI.
            if getattr(self.focused, "scrollable", False):
                self.focused.on_key(key)
            elif key in (Key.SCROLL_UP, Key.PAGE_UP, Key.CTRL_UP):
                self._scroll(-3)
            else:
                self._scroll(3)
        elif key == Key.TAB:
            self._cycle_focus(1)
        elif key == Key.SHIFT_TAB:
            self._cycle_focus(-1)
        elif key in self._key_handlers:
            result = self._key_handlers[key]()
            if result == "quit":
                self._should_quit = True
        elif self.focused:
            self.focused.on_key(key)

    def _dispatch_mouse(self, event):
        """Route a mouse event to the global hook then the widget under it.
        Coordinates are adjusted for scroll (overlays are screen-fixed) before
        either sees them."""
        modal = self._topmost_modal()
        event.row += 0 if modal else self.scroll_y
        if isinstance(event, MouseMove) and self._debug_log is not None:
            self._last_mouse_pos = (event.col, event.row)
        # Elements mode: the DevTools panel is open, its own Elements tab is
        # showing, and the event isn't over the panel's own chrome (a click
        # on a *different* DevTools tab must reach the tab bar below instead
        # of being treated as "select this widget" -- checked first via
        # _hit_widget so a click on the panel itself never reaches here) or
        # the Splitter's own divider bar between it and the app (Splitter.
        # contains() only ever matches the bar itself, never either pane's
        # own area -- see its docstring -- so this doesn't also exclude the
        # real app content Elements needs to hover/click in the first pane).
        elements_active = (
            modal is None  # a modal (e.g. a ConfirmDialog) must never lose
            # a click to Elements just because it's also open
            and self._devtools_active
            and self._devtools_tabs is not None
            and self._devtools_tabs.selected_title == "Elements"
            and not self._devtools_splitter.contains(event.col, event.row)
            and self._hit_widget(
                self._devtools_panel, event.col, event.row, require_focusable=False
            )
            is None
        )
        if elements_active:
            # Inspecting takes over the mouse entirely -- like a modal takes
            # over the keyboard -- so a click never activates the widget
            # underneath and a hover never fires the app's own tooltips.
            if isinstance(event, MouseMove):
                if not self._selection_frozen:
                    target = self._hit_any(event.col, event.row)
                    if target is not self._selected_widget:
                        self._selected_widget = target
                        self._selection_seq += 1
                return
            if isinstance(event, MouseClick):
                target = self._hit_any(event.col, event.row)
                if target is not self._selected_widget:
                    self._selected_widget = target
                    self._selection_seq += 1
                self._selection_frozen = True
                return
            return  # drag/release swallowed too while inspecting

        # Coordinates mode: same guard shape as elements_active, but a click
        # is a one-shot action (copy to the clipboard), not a UI mode to
        # freeze/unfreeze -- so only MouseClick is handled; hover is left
        # completely alone (the real app's own tooltips/hover effects keep
        # working normally, unlike Elements, which deliberately takes over
        # hover to preview a selection).
        coords_active = (
            modal is None
            and self._devtools_active
            and self._devtools_tabs is not None
            and self._devtools_tabs.selected_title == "Coordinates"
            and not self._devtools_splitter.contains(event.col, event.row)
            and self._hit_widget(
                self._devtools_panel, event.col, event.row, require_focusable=False
            )
            is None
        )
        if coords_active and isinstance(event, MouseClick):
            from cozy_tui import clipboard

            clipboard.copy(f"x={event.col}, y={event.row}")
            self.toast(f"Copied x={event.col}, y={event.row}", level="success")
            return  # swallow -- never activates the real widget underneath
        if self._mouse_handler is not None and self._mouse_handler(event):
            return  # consumed by the global hook
        if isinstance(event, MouseClick):
            if self._default_logs:
                self.debug(f"Clicked on col: {event.col}, row: {event.row}")
            # A non-modal overlay (an actionable Toast's buttons) gets first
            # look at a left click, without ever touching self.focused --
            # reusing the normal _dispatch_click path would _set_focused()
            # it, silently stealing focus from whatever the user was
            # actually working in. Right-click keeps its own path below
            # (context menus over the base UI), unaffected.
            if modal is None and event.btn == 0:
                overlay_target = self._hit_non_modal_overlay(event.col, event.row)
                if overlay_target is not None:
                    overlay_target.on_mouse_click(event.col, event.row)
                    return
            self._dispatch_click(event, modal)
        elif isinstance(event, MouseDrag):
            if self._default_logs:
                self.debug(f"Dragged mouse on col: {event.col}, row: {event.row}")
            if self.focused is not None:
                self.focused.on_mouse_drag(event.col, event.row)
        elif isinstance(event, MouseRelease):
            if self.focused is not None:
                self.focused.on_mouse_release(event.col, event.row)
        elif isinstance(event, MouseMove):
            target = None
            if modal is None:
                target = self._hit_non_modal_overlay(event.col, event.row)
            if target is None:
                target = self._mouse_target(event.col, event.row, modal)
            # Only widgets that opted into motion receive enter/leave.
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
        self._set_focused(self._first_focusable(target) or target)
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
        # Disable every mouse mode on exit regardless of which we ended on (a
        # dynamic upgrade may have switched us to 1003 after setup). Turn the
        # *tracking* modes off before the SGR encoding (1006) — some terminals
        # (WezTerm) otherwise keep motion reporting on in the legacy encoding.
        mouse_off = "\033[?1003l\033[?1002l\033[?1000l\033[?1006l"
        enter = (
            f"\033[?1049h\033[2J\033[H\033[?25l\033[?7l{mouse_on}\033[?2004h\033[>4;1m"
            if self.full
            else f"\033[2J\033[H\033[?25l\033[?7l{mouse_on}\033[?2004h\033[>4;1m"
        )
        # Disable the mouse again after leaving the alt screen, in case the
        # terminal tracks mouse state per screen buffer.
        reset = f"\033[>4;0m\033[?2004l{mouse_off}\033[?7h\033[?25h"
        exit_ = f"{reset}\033[?1049l{mouse_off}" if self.full else f"{reset}{mouse_off}"
        return enter, exit_

    def run(self):
        enter, exit_ = self._setup_sequences()

        self.set_title(self.title)  # emit OSC 0 terminal tab title

        sys.stdout.write(enter)
        sys.stdout.flush()
        raw_state = enable_raw()
        # Discard input queued before raw mode took effect (e.g. a stale
        # window-creation focus event on Windows) — otherwise kbhit() reports
        # ready immediately, the tick loop below never gets a chance to run,
        # and read_key() blocks until a real key/mouse event arrives, freezing
        # any animation on its first frame until the user does something.
        flush_input()
        self._running = True

        # Safety net: restore the terminal on *any* exit, including a tab close
        # (SIGHUP) or kill (SIGTERM) that skips the finally below. Without this a
        # hard exit leaves mouse tracking on, spraying reports into the shell.
        cleaned = [False]

        def _restore_terminal():
            if cleaned[0]:
                return
            cleaned[0] = True
            try:
                restore(raw_state)
            finally:
                # A hard teardown (SIGHUP from a closed tab) can leave stdout as
                # a broken pipe; don't let that exception stop the SIGHUP/SIGTERM
                # handler from reaching its os._exit(1).
                try:
                    sys.stdout.write(exit_)
                    sys.stdout.flush()
                except Exception:
                    pass

        atexit.register(_restore_terminal)
        old_handlers = {}
        for _name in ("SIGHUP", "SIGTERM"):
            sig = getattr(signal, _name, None)
            if sig is None:
                continue
            try:  # signals only settable on the main thread
                old_handlers[sig] = signal.signal(
                    sig, lambda *_a: (_restore_terminal(), os._exit(1))
                )
            except (ValueError, OSError):
                pass
        crash_exc = None
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
                    fired = self._drain_workers()
                    if self._drain_timers(now):
                        fired = True
                    if fired:
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
                    timer_wait = self._next_timer_deadline(now)
                    if timer_wait is not None:
                        waits.append(timer_wait)
                    wait_input(max(0.0, min(waits)))

                self._cursor_on = True
                key = read_key()
                if not key:  # None or "" from focus/resize console events
                    continue
                self._dispatch_input(key)
                if self._should_quit:
                    break
        except (KeyboardInterrupt, EOFError):
            # EOFError: stdin was closed out from under us (e.g. redirected from
            # a closed pipe) — nothing left to read, so shut down cleanly rather
            # than leaving the terminal in raw mode or busy-looping.
            pass
        except Exception as exc:
            if not self.catch_errors:
                raise
            # Deferred past `finally` below: the crash screen is its own fresh
            # App and must not start until *this* app's terminal state (raw
            # mode, alt screen, mouse tracking) has been fully torn down.
            crash_exc = exc
        finally:
            self._running = False
            _restore_terminal()
            atexit.unregister(_restore_terminal)
            for sig, old in old_handlers.items():
                try:
                    signal.signal(sig, old)
                except (ValueError, OSError):
                    pass
            if self._debug_file is not None:
                try:
                    self._debug_file.close()
                except Exception:
                    pass

        if crash_exc is not None:
            # Deferred import: crash_screen imports App itself (a module-level
            # import here would be circular) and pulls in the widgets/rich
            # machinery, which apps that never crash need not load at all.
            from cozy_tui.crash_screen import show_traceback

            show_traceback(crash_exc)
