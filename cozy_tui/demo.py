"""Interactive Cozy TUI showcase — run it with ``python -m cozy_tui`` or
``cozy-tui demo``.

A multi-page tour: a top MenuBar, an animated header, a sidebar menu (↑/↓ to
switch pages), a content area, and a footer hint bar. Tab moves focus into
the current page, Enter/Space activate the focused control. Ctrl+T opens a
searchable theme picker (or use the Dropdown on the Selection page, or
File/View in the MenuBar) -- header/footer/tabs and every accented/muted
label recolor live. Ctrl+P opens the command palette. Ctrl+S saves the current
screen as a standalone SVG file. Quitting (Esc, File > Quit, the right-click
menu, or the palette) always asks for confirmation first.
"""

import os
import time

from cozy_tui import App, Style, Theme
from cozy_tui import __version__ as _VERSION
from cozy_tui import get_theme
from cozy_tui.events import Key
from cozy_tui.widget import Widget
from cozy_tui.widgets import (
    AnimatedLabel,
    Bindings,
    Box,
    Button,
    Checkbox,
    CheckItem,
    CheckList,
    Dropdown,
    GlowAnimation,
    HBox,
    Hyperlink,
    Image,
    Input,
    Label,
    ListItem,
    ListView,
    MenuBar,
    MenuItem,
    MenuSeparator,
    RadioItem,
    RadioSet,
    RightClickMenu,
    SearchBar,
    Slider,
    Spinner,
    Splitter,
    Table,
    Tabs,
    Tree,
    VBox,
)

GITHUB = "https://github.com/youssefahmed2017/cozy_tui"
PYPI = "https://pypi.org/project/cozy-tui/"
# Bundled next to this file (not a relative "cat.jpg") so `cozy-tui demo`
# finds it regardless of the caller's current directory.
CAT_JPG = os.path.join(os.path.dirname(__file__), "cat.png")
# Start from the active theme's colors and are mutated in place (by
# _sync_theme_visuals() in main()) on a theme switch -- every Label built
# from these shares the Style object, not a copy, so they all recolor.
MUTED = Style(fg=get_theme().muted)
ACCENT = Style(fg=get_theme().accent)
OK = Style(fg=get_theme().success)


class _FlexPanel(Widget):
    """Demo-only: a borderless block that paints its whole assigned rectangle
    with `style`'s background and a centered label -- used by page_flex() so
    growth from VBox/HBox `flex=` is actually *visible* as a solid colored
    area, not just three widgets sitting closer together.

    Deliberately not a `Box`: `Box` sizes itself in "virtual pixels" (divided
    by App.SCALE, typically 10) while VBox/HBox always query children's
    natural_width/height at scale=1 during layout -- nesting a `Box` inside a
    VBox/HBox misreads its size by a factor of ~10. This widget stores its
    size in plain cells instead, like Label/Input/Button already do, so it
    measures and grows correctly as a flex child.
    """

    def __init__(self, x, y, w, h, label, style):
        super().__init__(x, y, style, name="FlexPanel")
        self.w = w
        self.h = h
        self.label = label

    def natural_width(self, scale):
        return self.w

    def natural_height(self, scale):
        return self.h

    def dock_resize(self, w, h, scale):
        self.w = max(1, w)
        self.h = max(1, h)

    def draw(self, canvas):
        mid = self.h // 2
        for row in range(self.h):
            text = self.label.center(self.w)[: self.w] if row == mid else " " * self.w
            canvas.write(self.abs_x, self.abs_y + row, text, self.style)


# ── content pages ────────────────────────────────────────────────────────────
# Each builder fills the given content Box with that page's widgets. `app` is
# passed so pages can open overlays.


def page_welcome(app, box):
    box.add(Label(2, 1, "Welcome to the Cozy TUI demo!", ACCENT))
    box.add(
        Label(2, 3, "Cozy TUI is a lightweight, cross-platform Python TUI library.")
    )
    box.add(
        Label(2, 4, "Every frame is drawn into a cell grid and diffed to the terminal.")
    )
    box.add(Label(2, 6, "Use ↑/↓ in the sidebar to explore. Tab dives into a page."))
    box.add(Hyperlink(2, 8, "★ Star on GitHub", GITHUB))
    box.add(Hyperlink(24, 8, "Cozy TUI on PyPI", PYPI))
    box.add(Label(2, 10, f"version {_VERSION}", MUTED))
    keys = Bindings(
        2,
        12,
        {
            "Navigation": {"↑ / ↓": "Switch page", "Tab": "Focus a control"},
            "Global": {
                "Enter / Space": "Activate",
                "Ctrl+T": "Change theme",
                "Ctrl+P": "Command palette",
                "Ctrl+S": "Save screenshot (SVG)",
                "Esc": "Quit (asks to confirm)",
            },
            "Debug": {"F12": "Toggle Cozy DevTools"},
        },
        title="Keys",
    )
    box.add(keys)

    # Beside the text (not stacked below the Keys legend) -- this page is a
    # plain Box, not a ScrollView, so anything that makes the page taller
    # than the terminal is simply unreachable, with no way to scroll to it.
    # x=70 clears the widest line above ("Every frame is drawn..." ends at
    # column 67); size is picked so the square photo renders at the correct
    # proportions (cols : rows*2 == 1:1 for a 1:1 source, matching Image's
    # own auto-fit math) instead of a taller box distorting it.
    box.add(Label(70, 1, "Image (Pillow, cached quadrant blocks):", ACCENT))
    box.add(Image(70, 2, CAT_JPG, size="480x240"))


def page_inputs(app, box):
    box.add(Label(2, 1, "Text input, password masking, and toggles:", ACCENT))
    box.add(Label(2, 3, "Name:"))
    name = Input(9, 3, 26, placeholder="your name…")
    box.add(name)
    box.add(Label(2, 5, "Pass:"))
    box.add(Input(9, 5, 26, placeholder="secret", masked=True))
    box.add(Checkbox(2, 7, "Subscribe to updates"))
    box.add(Checkbox(2, 8, "Enable telemetry"))

    box.add(Label(40, 3, "Volume (Slider):", ACCENT))
    volume = Slider(40, 4, minimum=0, maximum=100, value=70, step=1, width=24)
    box.add(volume)
    volume_label = Label(40, 6, "", MUTED)
    volume.on_change(lambda v: setattr(volume_label, "text", f"volume: {v}"))
    volume_label.text = f"volume: {volume.get()}"
    box.add(volume_label)
    app.set_tooltip(volume, "Left/Right to adjust, or drag the handle")

    out = Label(2, 11, "", OK)
    # Hover reacts per-widget: on_enter/on_leave opt just this button into
    # mouse-motion tracking — no app-wide flag needed.
    hover_note = Label(2, 13, "· hover the Greet button ·", MUTED)
    greet = Button(2, 10, "Greet")
    greet.on_click(lambda b: setattr(out, "text", f"Hi, {name.value or 'friend'}! 👋"))
    greet.on_enter(
        lambda b: setattr(hover_note, "text", "· hovering (per-widget mouse_moves) ·")
    )
    greet.on_leave(lambda b: setattr(hover_note, "text", "· hover the Greet button ·"))
    box.add(greet)
    box.add(out)
    box.add(hover_note)


def page_selection(app, box):
    box.add(Label(2, 1, "Language (ListView):", ACCENT))
    box.add(
        ListView(
            2,
            2,
            [
                ListItem("Python", "py"),
                ListItem("Rust", "rs"),
                ListItem("Go", "go"),
                ListItem("Zig", "zig"),
            ],
            height=4,
        )
    )
    box.add(Label(2, 7, "Theme (Dropdown):", ACCENT))
    theme_dropdown = Dropdown(
        2,
        8,
        [ListItem(mode.title(), mode) for mode in Theme.MODES],
        placeholder="choose...",
    )
    theme_dropdown.set(get_theme().mode)
    # Just activates the theme; header/footer/tabs/ACCENT/MUTED/OK are
    # re-synced by main()'s periodic poll, the same path Ctrl+T/Ctrl+P use.
    theme_dropdown.on_change(lambda mode: Theme(mode=mode).activate())
    box.add(theme_dropdown)

    box.add(Label(28, 1, "Toppings (CheckList):", ACCENT))
    box.add(
        CheckList(
            28,
            2,
            [
                CheckItem("Cheese"),
                CheckItem("Mushroom", checked=True),
                CheckItem("Olives"),
                CheckItem("Peppers"),
            ],
            height=4,
        )
    )

    box.add(Label(30, 7, "Question/Answer (RadioSet):", ACCENT))
    box.add(Label(30, 8, text="What is 5 x 5?"))
    box.add(
        RadioSet(
            items=[
                RadioItem(text="4", value=4),
                RadioItem(text="5", value=5),
                RadioItem(text="25", value=25),
            ],
            x=30,
            y=9,
        )
    )

    box.add(Label(2, 13, "Widgets (SearchBar, fuzzy):", ACCENT))
    widget_names = [
        "Button", "Checkbox", "Slider", "Input", "ListView", "Dropdown",
        "CheckList", "RadioSet", "Table", "Tree", "Tabs", "Splitter",
        "MenuBar", "RightClickMenu", "Toast", "Tooltip", "ScrollView",
        "Collapsible", "ProgressBar", "Spinner", "SearchBar",
    ]  # fmt: skip
    search_out = Label(2, 21, "", MUTED)
    search = SearchBar(
        2,
        14,
        widget_names,
        width=30,
        height=6,
        placeholder="try 'cl' or 'rcm'...",
        fuzzy_searching=True,
    )
    search.on_select(lambda v: setattr(search_out, "text", f"picked: {v}"))
    box.add(search)
    box.add(search_out)


def page_data(app, box):
    box.add(Label(2, 1, "Table:", ACCENT))
    tbl = Table(2, 2, height=3, show_border=True)
    tbl.add_column("Package", width=12)
    tbl.add_column("Kind", width=8)
    tbl.add_column("Stars", width=7, align="right")
    tbl.add_row("Cozy TUI", "TUI", "★★★★")
    tbl.add_row("Rich", "render", "★★★★★")
    tbl.add_row("Textual", "TUI", "★★★★★")
    box.add(tbl)

    box.add(Label(2, 9, "Tree:", ACCENT))
    tree = Tree(2, 10, connectors=True)
    proj = tree.add("cozy_tui")
    proj.expand()
    widgets = proj.add("widgets")
    widgets.expand()
    widgets.add("Button")
    widgets.add("Hyperlink")
    proj.add("app.py")
    box.add(tree)

    box.add(Label(2, 17, "Table (width=): drag the bar or use ←/→ to scroll", ACCENT))
    wide_tbl = Table(2, 18, width=34, show_border=True)
    wide_tbl.add_column("Package", width=14)
    wide_tbl.add_column("Kind", width=10)
    wide_tbl.add_column("Stars", width=9, align="right")
    wide_tbl.add_column("License", width=12)
    wide_tbl.add_column("Description", width=24)
    wide_tbl.add_row("Cozy TUI", "TUI", "★★★★", "MIT", "From-scratch terminal UI")
    wide_tbl.add_row("Rich", "render", "★★★★★", "MIT", "Rich text and formatting")
    wide_tbl.add_row("Textual", "TUI", "★★★★★", "MIT", "Full-featured TUI framework")
    box.add(wide_tbl)


def page_layout(app, box):
    box.add(Label(2, 1, "Splitter: drag the ┃ bar to resize these two panes.", ACCENT))

    # left/right share app.style (same object, not a copy) so a theme switch
    # recolors them too, the same reason header/footer/tabs do in main().
    left = Box(0, 0, "1x1", title="Font Size", border="rounded", style=app.style)
    left.add(Label(2, 1, "A Slider inside a Splitter pane:"))
    size_slider = Slider(2, 2, minimum=8, maximum=32, value=14, step=1, width=24)
    left.add(size_slider)
    size_label = Label(2, 4, "", MUTED)
    left.add(size_label)
    size_slider.on_change(lambda v: setattr(size_label, "text", f"font-size: {v}px"))
    size_label.text = f"font-size: {size_slider.get()}px"

    right = Box(0, 0, "1x1", title="Ratio", border="rounded", style=app.style)
    right.add(Label(2, 1, "Drag the bar, or click it then", MUTED))
    right.add(Label(2, 2, "Left/Right/Home/End.", MUTED))
    ratio_label = Label(2, 4, "", MUTED)
    right.add(ratio_label)

    splitter = Splitter(2, 3, "740x180", left, right, min_size=20)
    box.add(splitter)

    def _refresh_ratio():
        ratio_label.text = f"ratio: {splitter.get_ratio():.2f}"

    app.every(0.1, _refresh_ratio)
    _refresh_ratio()


def page_flex(app, box):
    box.add(
        Label(
            2,
            1,
            "Flex layout: VBox/HBox `.add(widget, flex=N)` grows children by weight.",
            ACCENT,
        )
    )
    box.add(
        Label(
            2,
            2,
            "1:2:3 ratio below, live on resize -- a plain VBox/HBox can't do this:",
            ACCENT,
        )
    )

    weights_row = HBox(2, 4, gap=1)
    weighted = []
    for n, color in ((1, "blue"), (2, "magenta"), (3, "green")):
        panel = _FlexPanel(0, 0, 1, 3, "", Style(fg="white", bg=color, styles=["bold"]))
        weights_row.add(panel, flex=n)
        weighted.append((panel, n))
    box.add(weights_row)

    def _resize_weights_row():
        # This page is a Tabs panel, which has no dock() of its own (unlike a
        # real Box) -- so the row's target width is driven directly off the
        # live terminal width instead. That's what proves the 1:2:3 ratio is
        # actually recomputed on a resize, not three widgets that just
        # happen to look proportional right now.
        avail_w = max(3, app.cols - weights_row.abs_x - 2)
        weights_row.dock_resize(avail_w, 3, app.SCALE)
        weights_row.natural_width(
            app.SCALE
        )  # force _arrange() so panel.w is fresh below
        for panel, n in weighted:
            panel.label = f"flex={n} ({panel.w}c)"

    app.every(0.2, _resize_weights_row)
    _resize_weights_row()

    box.add(
        Label(
            2,
            8,
            "Fixed frame: header/footer pinned, flex=1 fills the middle, live:",
            ACCENT,
        )
    )

    frame = Box(2, 9, "300x40", title="fixed frame", border="rounded", style=app.style)
    frame_col = VBox(0, 0)
    frame_col.add(Label(0, 0, "Header (flex=0)", ACCENT))
    # VBox only redistributes its main axis (height); the cross axis (width)
    # isn't stretched, so the panel's baseline width is set directly to span
    # the frame instead of relying on flex for that dimension too.
    content = _FlexPanel(
        0,
        0,
        26,
        1,
        "flex=1 -- grows to fill",
        Style(fg="black", bg="bright_cyan", styles=["bold"]),
    )
    frame_col.add(content, flex=1)
    frame_col.add(Label(0, 0, "Footer (flex=0)", MUTED))
    frame.dock(frame_col, "fill")
    box.add(frame)


def page_overlays(app, box):
    box.add(Label(2, 1, "Overlays float above everything and confine focus:", ACCENT))
    info = Label(2, 5, "", OK)

    def open_dialog(_b):
        dlg = Box(0, 0, "420x140", title="Confirm", border="rounded")
        dlg.add(Label(2, 1, "This is a centered, dimmed modal dialog."))
        dlg.add(Button(2, 3, "Cancel").on_click(lambda b: app.close_overlay(dlg)))
        dlg.add(
            Button(13, 3, "OK", style=Style(fg="white", bg="blue")).on_click(
                lambda b: (
                    setattr(info, "text", "Dialog confirmed ✔"),
                    app.close_overlay(dlg),
                )
            )
        )
        app.open_overlay(dlg, close_on_click_outside=True)

    box.add(Button(2, 3, "Open dialog").on_click(open_dialog))
    box.add(
        Button(16, 3, "Prompt…").on_click(
            lambda b: app.prompt(
                "Type something:",
                on_submit=lambda t: setattr(info, "text", f"You typed: {t}"),
            )
        )
    )
    box.add(info)

    # Toasts are transient overlays; a Spinner shows background work in flight.
    box.add(Label(2, 8, "Notifications & background work:", ACCENT))
    levels = ["info", "success", "warning", "error"]
    state = {"n": 0, "busy": False}

    def notify(_b):
        level = levels[state["n"] % len(levels)]
        state["n"] += 1
        app.toast(f"This is a {level} toast.", level=level)

    spinner = Spinner(38, 10, label="Loading...", spinner="clock")

    def load(_b):
        if state["busy"]:
            return
        state["busy"] = True
        box.add(spinner)  # appears and self-animates while the worker runs

        def done(rows):
            state["busy"] = False
            if spinner in box.children:
                box.children.remove(spinner)
            app.toast(f"Loaded {rows} rows.", level="success")

        app.run_worker(lambda: (time.sleep(1.5), 128)[1], on_result=done)

    notify_btn = Button(2, 10, "Notify").on_click(notify)
    box.add(notify_btn)
    app.set_tooltip(notify_btn, "Pops a toast, cycling info/success/warning/error")
    box.add(Button(13, 10, "Load data").on_click(load))

    box.add(Label(2, 13, "Delete something (ConfirmDialog):", ACCENT))
    confirm_out = Label(2, 15, "", MUTED)

    def ask_delete(_b):
        app.confirm(
            "Delete the selected item?",
            default=False,
            on_yes=lambda: setattr(confirm_out, "text", "Deleted ✔"),
            on_no=lambda: setattr(confirm_out, "text", "Cancelled"),
        )

    box.add(Button(2, 14, "Delete…").on_click(ask_delete))
    box.add(confirm_out)

    box.add(Label(2, 17, "Delete with Undo (Toast actions):", ACCENT))
    undo_out = Label(2, 19, "", MUTED)

    def delete_with_undo(_b):
        def undo():
            undo_out.text = "Restored ↩"

        app.toast(
            "Item deleted",
            actions=[("Undo", undo), ("Dismiss", None)],
            duration=5.0,
        )
        undo_out.text = "Deleted -- Undo in the toast, or wait 5s"

    box.add(Button(2, 18, "Delete item…").on_click(delete_with_undo))
    box.add(undo_out)


def page_about(app, box):
    box.add(Label(2, 1, "Cozy TUI", ACCENT))
    box.add(Label(2, 3, "A lightweight, cross-platform Python TUI library."))
    box.add(Label(2, 4, "Windows Console API + POSIX termios, built-in clipboard,"))
    box.add(Label(2, 5, "Unicode-aware rendering, overlays, and dock layout."))
    box.add(Hyperlink(2, 7, "Documentation", GITHUB + "#readme"))
    box.add(Hyperlink(2, 8, "GitHub", GITHUB))
    box.add(Hyperlink(2, 9, "PyPI", PYPI))
    box.add(Label(2, 11, f"Made with Cozy TUI {_VERSION}", MUTED))


PAGES = [
    ("Welcome", page_welcome),
    ("Inputs", page_inputs),
    ("Selection", page_selection),
    ("Data", page_data),
    ("Layout", page_layout),
    ("Flex", page_flex),
    ("Overlays", page_overlays),
    ("About", page_about),
]


def main() -> None:
    # No explicit style=: defaults to the active theme's style, so the demo
    # itself picks up whatever theme was set before main() ran.
    app = App(full=True, title="Cozy TUI Demo", debug=True)
    app.debug(f"Cozy TUI {_VERSION} demo started — F12 or right-click > Open DevTools")
    app.tick_interval = 0.06  # keep the animated header running

    def _confirm_quit():
        # default=False: an accidental Enter highlights "No" first, so it
        # takes a deliberate choice (or Y) to actually quit.
        app.confirm("Quit the demo?", on_yes=app.quit, default=False)

    def _open_file(_it):
        app.pick_file(
            on_select=lambda path: app.toast(f"Picked: {path}", level="success")
        )

    def _open_folder(_it):
        app.pick_file(
            mode="directory",
            on_select=lambda path: app.toast(f"Folder: {path}", level="success"),
        )

    menu_bar = MenuBar(
        0,
        0,
        [
            (
                "File",
                [
                    MenuItem("Open File…", icon="📄", on_select=_open_file),
                    MenuItem("Open Folder…", icon="📁", on_select=_open_folder),
                    MenuSeparator(),
                    MenuItem(
                        "Save Screenshot",
                        icon="📸",
                        shortcut="Ctrl+S",
                        on_select=lambda _it: app._quick_screenshot(),
                    ),
                    MenuSeparator(),
                    MenuItem(
                        "Quit",
                        icon="🚪",
                        shortcut="Esc",
                        on_select=lambda _it: _confirm_quit(),
                    ),
                ],
            ),
            (
                "View",
                [
                    MenuItem(
                        "Theme",
                        icon="🎨",
                        submenu=[
                            MenuItem(
                                mode.title(),
                                on_select=lambda _it, m=mode: Theme(mode=m).activate(),
                            )
                            for mode in Theme.MODES
                        ],
                    ),
                    MenuSeparator(),
                    MenuItem(
                        "Command Palette",
                        icon="⌘",
                        shortcut="Ctrl+P",
                        on_select=lambda _it: app.open_command_palette(),
                    ),
                    MenuItem(
                        "Toggle DevTools",
                        icon="🐞",
                        shortcut="F12",
                        on_select=lambda _it: app.toggle_devtools(),
                    ),
                ],
            ),
        ],
    )
    app.dock(menu_bar, "top")

    # header/footer/tabs share app.style (same object, not a copy): a theme
    # switch mutates app.style once, and every widget pointing at it picks
    # up the new colors on the next frame.
    header = Box(0, 0, "10x10", title="✨ Cozy TUI", border="rounded", style=app.style)
    glow = GlowAnimation(color_template="blue", speed=0.08)
    header.add(
        AnimatedLabel(
            1,
            1,
            f"  Cozy TUI {_VERSION}  —  a cozy, cross-platform terminal UI toolkit",
            animation=glow,
        )
    )
    app.dock(header, "top")

    footer = Box(0, 0, "10x10", title="keys", border="rounded", style=app.style)
    hint = Label(1, 1, "", MUTED)
    # Label wraps ("laps") onto extra lines by default when it's wider than
    # its Box, growing the Box's own border to fit -- but footer's height is
    # fixed by the dock system (based on its un-wrapped size), so a wrapped
    # 2nd line pushed the bottom border off-screen instead. This footer is a
    # single-line status bar: it should truncate on narrow terminals, not wrap.
    hint.laps = False
    footer.add(hint)
    app.dock(footer, "bottom")

    # Each page is a tab; only the active panel is drawn, focusable, and clickable.
    tabs = Tabs(0, 0, "10x10", style=app.style, accent=get_theme().accent)
    for name, builder in PAGES:
        builder(app, tabs.add_tab(name))
    app.dock(tabs, "fill")

    # Theme can change from several places (Ctrl+T's palette, Ctrl+P's
    # "Change Theme" command, the MenuBar's View > Theme, the Selection
    # page's Theme Dropdown) -- rather than hooking every one of them
    # individually, a periodic poll notices whenever the active theme's mode
    # has actually changed and re-syncs everything that doesn't read it
    # fresh every frame.
    _last_synced_mode = {"mode": get_theme().mode}

    def _sync_theme_visuals():
        theme = get_theme()
        app.style.fg = theme.style.fg
        app.style.bg = theme.style.bg  # already carries Style's "_bg" suffix
        ACCENT.fg = theme.accent
        MUTED.fg = theme.muted
        OK.fg = theme.success
        tabs.accent = theme.accent
        app.invalidate()
        _last_synced_mode["mode"] = theme.mode

    def _poll_theme():
        if get_theme().mode != _last_synced_mode["mode"]:
            _sync_theme_visuals()

    app.every(0.15, _poll_theme)

    def on_tab(index):
        hint.text = (
            f"  {PAGES[index][0]}     ←/→ or click: switch tab    Tab: into panel    "
            "Right-click: menu    Enter/Space: activate    Esc: quit (confirms)"
        )
        app.debug(f"switched to tab {index!r}: {PAGES[index][0]}")

    tabs.on_change(on_tab)
    on_tab(0)

    # A right-click anywhere pops up a context menu whose submenu jumps to a tab.
    menu = RightClickMenu(
        [
            MenuItem(
                "Go to tab",
                icon="📄",
                submenu=[
                    MenuItem(name, on_select=lambda i, n=idx: tabs.select(n))
                    for idx, (name, _) in enumerate(PAGES)
                ],
            ),
            MenuSeparator(),
            MenuItem(
                "Change Theme",
                icon="🎨",
                shortcut="Ctrl+T",
                on_select=lambda _: app.open_theme_palette(),
            ),
            MenuItem(
                "Open DevTools", icon="🐞", on_select=lambda _: app.toggle_devtools()
            ),
            MenuSeparator(),
            MenuItem(
                "Quit", icon="🚪", shortcut="Esc", on_select=lambda i: _confirm_quit()
            ),
        ]
    )

    def on_right_click(col, row, w):
        app.debug(f"right-click at ({col}, {row}) on {type(w).__name__ if w else None}")
        menu.open_at(app, col, row)

    app.on_right_click(on_right_click)

    # App registers its own "Quit" -> self.quit by default; re-registering
    # the same name overrides it, so Ctrl+P's Quit confirms too.
    app.register_command("Quit", _confirm_quit, description="Quit the application")

    app.focus(tabs.bar)
    app.on_key(Key.ESC, _confirm_quit)
    app.run()


if __name__ == "__main__":
    main()
