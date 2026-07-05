"""Interactive Cozy TUI showcase — run it with ``python -m cozy_tui`` or
``cozy-tui demo``.

A multi-page tour: an animated header, a sidebar menu (↑/↓ to switch pages),
a content area, and a footer hint bar. Tab moves focus into the current page,
Enter/Space activate the focused control, and Esc quits.
"""

from cozy_tui import App, Style
from cozy_tui import __version__ as _VERSION
from cozy_tui.events import Key
from cozy_tui.widgets import (AnimatedLabel, Bindings, Box, Button, Checkbox,
                              CheckItem, CheckList, Dropdown, GlowAnimation,
                              Hyperlink, Input, Label, ListItem, ListView,
                              MenuItem, MenuSeparator, RadioItem, RadioSet,
                              RightClickMenu, Table, Tabs, Tree)

GITHUB = "https://github.com/youssefahmed2017/cozy_tui"
PYPI = "https://pypi.org/project/cozy-tui/"
MUTED = Style(fg="bright_black")
ACCENT = Style(fg="bright_cyan")
OK = Style(fg="bright_green")


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
    box.add(
        Bindings(
            2,
            12,
            {
                "Navigation": {"↑ / ↓": "Switch page", "Tab": "Focus a control"},
                "Global": {"Enter / Space": "Activate", "Esc": "Quit"},
            },
            title="Keys",
        )
    )


def page_inputs(app, box):
    box.add(Label(2, 1, "Text input, password masking, and toggles:", ACCENT))
    box.add(Label(2, 3, "Name:"))
    name = Input(9, 3, 26, placeholder="your name…")
    box.add(name)
    box.add(Label(2, 5, "Pass:"))
    box.add(Input(9, 5, 26, placeholder="secret", masked=True))
    box.add(Checkbox(2, 7, "Subscribe to updates"))
    box.add(Checkbox(2, 8, "Enable telemetry"))
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
    box.add(
        Dropdown(
            2,
            8,
            [
                ListItem("Dark", "dark"),
                ListItem("Light", "light"),
                ListItem("Solarized", "sol"),
            ],
            placeholder="choose...",
        )
    )

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


def page_overlays(app, box):
    box.add(Label(2, 1, "Overlays float above everything and confine focus:", ACCENT))
    info = Label(2, 6, "", OK)

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


def page_about(app, box):
    box.add(Label(2, 1, "Cozy TUI", ACCENT))
    box.add(Label(2, 3, "A lightweight, cross-platform Python TUI library."))
    box.add(Label(2, 4, "Windows Console API + POSIX termios, built-in clipboard,"))
    box.add(Label(2, 5, "Unicode-aware rendering, overlays, and dock layout."))
    box.add(Hyperlink(2, 7, "Documentation", GITHUB + "#readme"))
    box.add(Hyperlink(2, 8, "GitHub", GITHUB))
    box.add(Hyperlink(2, 9, "PyPI", PYPI))
    box.add(Label(2, 11, f"Made with Cozy TUI {_VERSION} 💜", MUTED))


PAGES = [
    ("Welcome", page_welcome),
    ("Inputs", page_inputs),
    ("Selection", page_selection),
    ("Data", page_data),
    ("Overlays", page_overlays),
    ("About", page_about),
]


def main() -> None:
    app = App(
        full=True,
        style=Style(fg="white", bg="black"),
        title="Cozy TUI Demo",
    )
    app.tick_interval = 0.06  # keep the animated header running

    header = Box(0, 0, "10x10", title="✨ Cozy TUI", border="rounded")
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

    footer = Box(0, 0, "10x10", title="keys", border="rounded")
    hint = Label(1, 1, "", MUTED)
    footer.add(hint)
    app.dock(footer, "bottom")

    # Each page is a tab; only the active panel is drawn, focusable, and clickable.
    tabs = Tabs(0, 0, "10x10", accent="bright_cyan")
    for name, builder in PAGES:
        builder(app, tabs.add_tab(name))
    app.dock(tabs, "fill")

    def on_tab(index):
        hint.text = (
            f"  {PAGES[index][0]}     ←/→ or click: switch tab    Tab: into panel    "
            "Right-click: menu    Enter/Space: activate    Esc: quit"
        )

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
            MenuItem("Quit", icon="🚪", shortcut="Esc", on_select=lambda i: app.quit()),
        ]
    )
    app.on_right_click(lambda col, row, w: menu.open_at(app, col, row))

    app.focus(tabs.bar)
    app.on_key(Key.ESC, lambda: "quit")
    app.run()


if __name__ == "__main__":
    main()
