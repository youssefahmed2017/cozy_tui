"""Internal: the F12 Cozy DevTools panel -- Elements / Console / Performance
/ Tree, unified behind one key instead of three (F3/F12/Ctrl+Shift+D used to
open three separate overlays; now everything lives here). Gated behind
App(debug=True).

Not an overlay at all -- a real docked pane, split from the app's own
content by a draggable `Splitter` (see `App.toggle_devtools`), so the app's
content genuinely shares the screen instead of being covered. `_AppContentPane`
(below) is what makes this possible: it wraps the app's *actual* pre-existing
top-level widgets so Splitter can treat "the whole app" as a single pane,
re-running the same `dock_layout()` App itself uses (just scoped to whatever
rectangle Splitter assigns it) so the app's own top/bottom/fill docks
correctly reflow into a narrower width, the same way a real browser page
reflows when DevTools opens.

Because DevTools' own tab bar/Tree are therefore real, focusable widgets
reachable through the normal hit-test/click-dispatch path (not overlay
plumbing), clicking them Just Works via the ordinary mechanism every other
focusable widget already uses: `App._dispatch_click` finds them via
`_hit_test()` and calls `_set_focused()` itself, so the clicked tab/row gets
the normal focused-widget highlight and, as a bonus, keyboard routing
(Left/Right then switches tabs via `_TabBar.on_key`, matching every other
`Tabs` instance) -- no special-casing needed here at all. Elements' hover/
click-to-freeze behavior on the *real app's* widgets is the one thing that's
still inherently special regardless of this restructuring (see
`App._dispatch_mouse`'s `elements_active` branch and `App._hit_any`).
Console/Performance are read-only either way.
"""

from cozy_tui._devtools_edit import EditError, apply_snippet, build_snippet
from cozy_tui._dock import dock_layout
from cozy_tui.style import Style
from cozy_tui.theme import get_theme
from cozy_tui.widget import Widget
from cozy_tui.widgets import Box, Button, CodeInput, Label, ScrollView, Tabs, Tree

# Fixed refresh cadence requested while open, via App.request_frame -- the
# same mechanism AnimatedLabel already uses to keep the loop ticking during
# animation. Without this, FPS/the status bar would only refresh when
# something else causes a render, freezing on stale numbers the rest of the
# time -- correct for this deliberately idle-when-quiet engine, but useless
# for a *live* HUD.
_REFRESH_INTERVAL = 1 / 20


def _field(rows, y, label, value):
    rows.append(Label(0, y, f"{label}: {value}" if label else str(value)))
    return y + 1


class _LiveLog(ScrollView):
    """Self-updating ScrollView showing App._debug_log (the Console tab).
    Only rebuilds its rows when `App._debug_seq` has moved since it last
    drew, so `app.debug(...)` calls -- which may happen far more often than
    the panel is ever open -- do no work of their own; the sync cost lands
    on this widget's own `draw()`."""

    def __init__(self, app, x, y, size):
        super().__init__(x, y, size, autoscroll=True)
        self._app = app
        self._synced_seq = -1

    def draw(self, canvas):
        if self._synced_seq != self._app._debug_seq:
            self._synced_seq = self._app._debug_seq
            self.clear()
            for i, line in enumerate(self._app._debug_log):
                self.add(Label(0, i, line))
        super().draw(canvas)


class _ElementsView(Widget):
    """The Elements tab: a live property panel for `app._selected_widget`,
    plus a **live editor** for it (see `_devtools_edit.py`).
    Rebuilds its rows only when `app._selection_seq` has moved since it last
    drew -- same seq-gated pattern `_LiveLog` uses -- so moving the mouse
    over widgets that resolve to the *same* selection costs nothing extra
    per frame. No border of its own (the Tabs panel already frames it), so
    it's a bare `Widget` managing a plain list of `Label` children rather
    than a `Box`.

    The editor's three widgets (Input + two Buttons) are built **once**, in
    `__init__`, and only repositioned/refilled by `_rebuild()` -- unlike the
    property Labels, which are thrown away and recreated. Rebuilding them
    too would hand `App.focused` a discarded orphan the moment a rebuild
    happened while the editor was focused (a click on a different widget
    does exactly that), leaving keystrokes going to an Input that is no
    longer drawn.
    """

    def __init__(self, app):
        super().__init__(0, 0)
        self._app = app
        self.children: list = []
        self._synced_seq = -1
        # Same approximation _LiveLog uses for its own width: the real
        # Splitter-assigned width isn't known until the first dock_resize(),
        # and a cell or two of slack is cosmetic (the Input clips itself).
        editor_w = max(18, int(app.cols * 0.38) - 8)
        # A CodeInput, not a plain Input: the snippet *is* Python, so it reads
        # as highlighted source whenever the editor isn't focused, and falls
        # back to plain text with a cursor/selection while it is being typed
        # in (the same trade MarkdownInput makes).  background=False so it
        # doesn't paint a theme-colored slab inside the panel's own chrome.
        self.editor = CodeInput(
            0, 0, editor_w, lang="python", background=False, style=app.style
        )
        self._apply_button = Button(0, 0, "Apply", width=9).on_click(self._apply)
        self._revert_button = Button(0, 0, "Revert", width=10).on_click(self._revert)
        self._message = Label(0, 0, "")

    # ── live editing ─────────────────────────────────────────────────────────

    def _set_message(self, text, color):
        self._message.text = text
        self._message.style = Style(fg=color)

    def _apply(self, _button=None):
        widget = self._app._selected_widget
        if widget is None:
            return
        try:
            changed = apply_snippet(widget, self.editor.value)
        except EditError as exc:
            # Reported in the panel, never raised: this runs from a Button
            # callback inside the render loop, where an exception would take
            # down the whole app over a typo (cf. App._quick_screenshot,
            # which toasts its failures for the same reason).
            self._set_message(f"x {exc}", "bright_red")
            return
        # Re-read the widget rather than bumping _selection_seq and waiting
        # for draw(): this refreshes the read-only rows *and* normalizes the
        # snippet (so `x=2.0` echoes back as the int the widget now holds),
        # and doing it inline keeps the message below from being clobbered
        # by a rebuild on the next frame.
        self._rebuild()
        if changed:
            self._set_message(f"ok applied {', '.join(changed)}", "bright_green")
        else:
            self._set_message("no changes", "bright_black")

    def _revert(self, _button=None):
        self._rebuild()
        self._set_message("reverted", "bright_black")

    def _rebuild(self):
        self._synced_seq = self._app._selection_seq
        self.children = []
        widget = self._app._selected_widget
        rows: list = []
        y = 0
        if widget is None:
            rows.append(Label(0, y, "No widget selected"))
        else:
            scale = self._app.SCALE
            width = widget.natural_width(scale)
            height = widget.natural_height(scale)
            on_screen = (
                0 <= widget.abs_x < self._app.cols
                and 0 <= widget.abs_y - self._app.scroll_y < self._app.rows
            )
            parent = widget.parent
            styles = ", ".join(widget.style.styles) if widget.style.styles else "-"
            rows.append(Label(0, y, f"Widget: {type(widget).__name__}"))
            y += 2
            y = _field(rows, y, "x", widget.x)
            y = _field(rows, y, "y", widget.y)
            y = _field(rows, y, "width", width)
            y = _field(rows, y, "height", height)
            y += 1
            y = _field(rows, y, "abs_x", widget.abs_x)
            y = _field(rows, y, "abs_y", widget.abs_y)
            y += 1
            y = _field(rows, y, "Focused", widget is self._app.focused)
            y = _field(rows, y, "Hovered", widget is self._app._hovered)
            y = _field(rows, y, "Visible", on_screen)
            y += 1
            y = _field(
                rows, y, "Parent", type(parent).__name__ if parent is not None else "-"
            )
            y = _field(rows, y, "Children", len(getattr(widget, "children", []) or []))
            y += 1
            rows.append(Label(0, y, "Style"))
            y += 1
            y = _field(rows, y, "fg", widget.style.fg or "-")
            y = _field(rows, y, "bg", widget.style.raw_bg or "-")
            y = _field(rows, y, "attrs", styles)
            if self._app._selection_frozen:
                y += 1
                rows.append(Label(0, y, "[frozen -- Esc to resume]"))
        for row in rows:
            self.add(row)
        if widget is not None:
            self._place_editor(y + 2)

    def _place_editor(self, y):
        """Lay the (persistent) editor widgets out below the property rows and
        refill the Input from the widget's current state."""
        muted = Style(fg="bright_black")
        self.add(Label(0, y, "Live edit", Style(styles=["bold"])))
        self.add(Label(0, y + 1, "edit a value, then Apply", muted))
        y += 3
        self.editor.value = build_snippet(self._app._selected_widget)
        self.editor.cursor_pos = min(self.editor.cursor_pos, len(self.editor.value))
        self.editor.y = y
        self.add(self.editor)
        y += self.editor.natural_height(self._app.SCALE) + 1
        self._apply_button.y = y
        self._revert_button.x = 11
        self._revert_button.y = y
        self.add(self._apply_button)
        self.add(self._revert_button)
        self._message.y = y + 2
        self.add(self._message)

    def add(self, widget):
        widget.parent = self
        self.children.append(widget)

    def draw(self, canvas):
        if self._synced_seq != self._app._selection_seq:
            self._rebuild()
            self._message.text = ""
        if canvas.focused is self.editor and not self._app._selection_frozen:
            # Typing into the editor freezes the selection: without this, a
            # stray mouse movement over the app would retarget Elements and
            # rebuild the snippet out from under the edit in progress.
            self._app._selection_frozen = True
        for child in self.children:
            child.draw(canvas)


class _PerformanceView(Widget):
    """The Performance tab: FPS/timings, rebuilt every draw() (unlike
    Elements/the log, these numbers are expected to change every frame it's
    open, so there's no seq to gate on)."""

    def __init__(self, app):
        super().__init__(0, 0)
        self._app = app
        self.children: list = []

    def add(self, widget):
        widget.parent = self
        self.children.append(widget)

    def _rebuild(self):
        app = self._app
        self.children = []
        mx, my = app._last_mouse_pos
        lines = [
            f"FPS      : {app._current_fps():.0f}",
            f"Widgets  : {app._count_widgets()}",
            f"Focused  : {type(app.focused).__name__ if app.focused else '-'}",
            f"Hovered  : {type(app._hovered).__name__ if app._hovered else '-'}",
            f"Mouse    : {mx},{my}",
            "",
            f"Frame    : {app._last_frame_ms:.1f} ms",
            f"Render   : {app._last_render_ms:.1f} ms",
            f"Layout   : {app._debug_layout_ms:.1f} ms",
        ]
        for i, line in enumerate(lines):
            self.add(Label(0, i, line))

    def draw(self, canvas):
        self._rebuild()
        for child in self.children:
            child.draw(canvas)


class _CoordinatesView(Widget):
    """The Coordinates tab: the live cursor position (`App._last_mouse_pos`,
    already tracked on every MouseMove whenever debug=True regardless of
    which tab is active -- see `App._dispatch_mouse`), rebuilt every draw()
    like Performance. Unlike Elements, clicking here is a one-shot action
    (copy `x=.., y=..` to the clipboard, see `App._dispatch_mouse`'s
    `coords_active` branch) rather than a mode you freeze/unfreeze, so there
    is no selection state to track -- this view is purely a live readout."""

    def __init__(self, app):
        super().__init__(0, 0)
        self._app = app
        self.children: list = []

    def add(self, widget):
        widget.parent = self
        self.children.append(widget)

    def _rebuild(self):
        app = self._app
        self.children = []
        mx, my = app._last_mouse_pos
        lines = [
            "Live position",
            "",
            f"x: {mx}",
            f"y: {my}",
            "",
            "Click anywhere in the app to copy",
            "these coordinates to your clipboard.",
        ]
        for i, line in enumerate(lines):
            self.add(Label(0, i, line))

    def draw(self, canvas):
        self._rebuild()
        for child in self.children:
            child.draw(canvas)


def _build_widget_tree(app) -> Tree:
    """A read-only, always-expanded snapshot of the live widget hierarchy: a
    synthetic "App" root (not itself selectable -- `metadata` stays `None`)
    with one child per top-level app widget, recursing into `.children`.
    `node.metadata` holds the actual widget instance, so picking a node can
    select it. Built once, when the Tree tab is first switched into (see
    `DevToolsPanel`) rather than every frame: rebuilding on every draw()
    would reset the always-expanded state relative to whatever a live
    diff/preserve scheme might otherwise track -- a fresh snapshot per visit
    is simpler and matches this being a "what does the tree look like"
    browser, not a continuously live feed like Console.

    Reads `app._devtools_content_pane.children`, not `app.widgets` --
    while DevTools is open, `app.widgets` is just `[the top-level Splitter]`
    (see `App.toggle_devtools`); the actual app content lives wrapped inside
    that pane. Showing DevTools' own internals (the Splitter, this very
    panel) here would be circular and useless."""
    tree = Tree(0, 0, connectors=True)
    root = tree.add("App")
    root.expand()

    def add_children(node, widget):
        child_node = node.add(type(widget).__name__)
        child_node.metadata = widget
        child_node.expand()
        for child in getattr(widget, "children", None) or ():
            add_children(child_node, child)

    for w in app._devtools_content_pane.children:
        add_children(root, w)
    return tree


class _AppContentPane(Widget):
    """Wraps the app's own pre-existing top-level widgets into a single pane
    so `Splitter` can treat "the whole app" as one of its two children (see
    `App.toggle_devtools`). Re-runs `dock_layout()` -- the exact function
    `App._apply_docks()` itself uses -- scoped to whatever rectangle
    `Splitter` assigns this pane via `dock_resize()`, instead of the full
    screen, so the app's own top/bottom/fill docks (a MenuBar, a header, a
    footer, a filled Tabs -- like the demo has) correctly reflow into a
    narrower width rather than clipping or overflowing.

    `.children` is the wrapped widget list itself (not a copy) -- the same
    list `App.add()` redirects into while this pane exists (see
    `App.toggle_devtools`), and the same list restored back onto
    `app.widgets` when DevTools closes. Exposing it as `.children` is what
    lets the *already-generic* `_hit_widget`/`_collect_focusables`/
    `_focusables_in` recursion (all of which recurse via
    `hasattr(widget, "children")`) reach into it for hit-testing and
    Tab-cycling with zero changes needed there.
    """

    def __init__(self, children: list):
        super().__init__(0, 0)
        self.children = children
        self._w = self._h = 0

    def dock_resize(self, w, h, scale) -> None:
        self._w, self._h = w, h

    def contains(self, col: int, row: int) -> bool:
        return (
            self.abs_x <= col < self.abs_x + self._w
            and self.abs_y <= row < self.abs_y + self._h
        )

    def draw(self, canvas) -> None:
        # (0, 0), not self.abs_x/abs_y: dock_layout()'s x/y are in whatever
        # coordinate space the widgets' own .x/.y live in -- since each
        # wrapped child's `parent` is this pane (see App.toggle_devtools),
        # abs_x already adds self.abs_x on top, exactly like Box._apply_docks
        # passes its own interior-relative (1, 1) rather than an absolute
        # screen position.
        items = [
            (w, w._dock[0], w._dock[1])
            for w in self.children
            if getattr(w, "_dock", None) is not None
        ]
        if items:
            dock_layout(items, 0, 0, self._w, self._h, canvas.SCALE)
        for child in self.children:
            child.draw(canvas)


class DevToolsPanel(Box):
    """The F12 panel: a title bar, a Tabs strip (Elements/Console/
    Performance/Coordinates/Tree), and a status bar pinned to the last row,
    always showing FPS/widget count/focus/theme regardless of which tab is
    active.
    """

    TAB_NAMES = ("Elements", "Console", "Performance", "Coordinates", "Tree")

    def __init__(self, app):
        # Placeholder size: Splitter calls dock_resize() with this pane's
        # real assigned rectangle every draw() (Box already supports being
        # externally dock_resize()'d -- used by both App.dock() and Splitter
        # alike), the same pattern demo.py's own page-switching Tabs already
        # relies on for its own placeholder "10x10".
        super().__init__(
            0, 0, "10x10", title="Cozy DevTools", border="rounded", style=app.style
        )
        self._app = app

        # dock() (not manual x/y) for both direct children of this Box --
        # it already handles the "children need x>=1/y>=1 to clear the
        # border" offset (see Box._apply_docks/dock_layout), the same
        # bug InspectorPanel/PerfOverlay needed a manual "+1" for last
        # session. Status docks first (reserves its 1-row band), Tabs then
        # fills whatever's left, in call order -- matching every other
        # dock() user in this codebase (see demo.py's header/footer/tabs).
        self._status = Label(0, 0, "")
        self.dock(self._status, "bottom")

        # Placeholder size: dock(..., "fill") calls Tabs.dock_resize() with
        # its real assigned rectangle every draw(), the same pattern
        # demo.py's own page-switching Tabs already relies on.
        self.tabs = Tabs(0, 0, "10x10", style=app.style)

        elements_panel = self.tabs.add_tab("Elements")
        self.elements = _ElementsView(app)
        elements_panel.add(self.elements)
        # Published on the App so _dispatch_input can tell "Esc while typing
        # in the live editor" from "Esc to unfreeze the selection" -- the
        # editor must not have its own text yanked away mid-edit by a key
        # that never reaches it.
        app._devtools_editor = self.elements.editor

        console_panel = self.tabs.add_tab("Console")
        # _LiveLog (a ScrollView) lives *inside* a Tabs panel, not directly
        # docked to this Box, so it needs an explicit size up front rather
        # than growing via dock_resize() -- and unlike this Box itself, it
        # won't track a *later* drag of the Splitter's divider either, only
        # whatever DevTools' assigned width happens to be when Console is
        # first opened. Approximated from the app's current terminal size
        # (DevTools' own default ~38% share, see App.toggle_devtools) since
        # the real Splitter-assigned width isn't known until the first
        # dock_resize(); a cell or two of slack is cosmetic only (ScrollView
        # clips its own content) -- properly tracking the divider would mean
        # making _LiveLog dock-managed within its own tab panel too, out of
        # scope for this pass.
        scale = app.SCALE
        console_w = max(20, int(app.cols * 0.38) - 6)
        console_h = max(10, app.rows - 6)
        console_panel.add(
            _LiveLog(app, 0, 0, f"{console_w * scale}x{console_h * scale}")
        )

        perf_panel = self.tabs.add_tab("Performance")
        perf_panel.add(_PerformanceView(app))

        coords_panel = self.tabs.add_tab("Coordinates")
        coords_panel.add(_CoordinatesView(app))

        self._tree_panel = self.tabs.add_tab("Tree")
        self._tree_built = False

        def _select_from_tree(node):
            # Selects and highlights (Elements/the highlight border pick it
            # up via the shared _selected_widget) but deliberately does NOT
            # switch to the Elements tab -- staying put lets you click
            # through several widgets in the tree in a row without being
            # bounced away each time; switch to Elements yourself for detail.
            widget = node.metadata
            if widget is None:
                return  # the synthetic "App" root isn't itself inspectable
            app._selected_widget = widget
            app._selection_seq += 1
            app._selection_frozen = True

        def _on_tab_change(index):
            if self.tabs._titles[index] == "Tree" and not self._tree_built:
                self._tree_built = True
                tree = _build_widget_tree(app)
                tree.on_select(_select_from_tree)
                self._tree_panel.add(tree)

        self.tabs.on_change(_on_tab_change)
        self.dock(self.tabs, "fill")

    def draw(self, canvas):
        app = self._app
        focus_name = type(app.focused).__name__ if app.focused else "-"
        self._status.text = (
            f"FPS: {app._current_fps():.0f} | Widgets: {app._count_widgets()} | "
            f"Focus: {focus_name} | Theme: {get_theme().mode.title()}"
        )
        canvas.request_frame(_REFRESH_INTERVAL)
        super().draw(canvas)


def draw_highlight(canvas, widget) -> None:
    """Tint the perimeter of `widget`'s bounding box directly in
    `canvas.buffer` -- the same "keep the char, change the style" technique
    `App._apply_backdrop()` already uses for the modal scrim, so it composes
    with the rest of the frame without going through `write()`'s
    scroll/overlay bookkeeping (the target widget is normal, scroll-affected
    content; the box just needs to line up with wherever it actually drew).

    Deliberately recolors the widget's own already-drawn characters instead
    of overwriting them with border-drawing glyphs -- for anything only 1-2
    rows tall (a tab strip, a Button, an Input), a "top" row and a "bottom"
    row are the *same* row(s) the widget's real content occupies, so drawing
    a literal box there would erase it entirely instead of framing it.
    Recoloring can never erase content, at any size.

    Uses `natural_width`/`natural_height` uniformly for the box, like most
    widgets' default `contains()` does. A few widgets with a custom
    `contains()` (`Box`, whose real hit box is `_bounds`, cached from its
    last draw) may be highlighted a cell or two off from their exact hit
    box -- an acceptable, documented limitation rather than a reason to give
    every widget a second, uniform bounding-box accessor.
    """
    scale = canvas.SCALE
    w = widget.natural_width(scale)
    h = widget.natural_height(scale)
    if w <= 0 or h <= 0:
        return
    x0 = widget.abs_x
    y0 = widget.abs_y - canvas.scroll_y
    x1 = x0 + w - 1
    y1 = y0 + h - 1
    accent = get_theme().accent
    rows, cols = len(canvas.buffer), len(canvas.buffer[0]) if canvas.buffer else 0

    def tint(x, y):
        if 0 <= y < rows and 0 <= x < cols:
            cell = canvas.buffer[y][x]
            # Style(bg=...) re-applies cell.style's internal "_bg" suffix, so
            # this must be seeded from raw_bg (unsuffixed) -- passing .bg
            # directly would double it up (e.g. "black_bg" -> "black_bg_bg").
            cell.style = Style(
                fg=accent, bg=cell.style.raw_bg, styles=["bold", "underline"]
            )

    for x in range(x0, x1 + 1):
        tint(x, y0)
        tint(x, y1)
    for y in range(y0, y1 + 1):
        tint(x0, y)
        tint(x1, y)
