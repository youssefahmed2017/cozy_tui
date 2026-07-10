"""Theme showcase — browse every built-in cozy_tui Theme, grouped by
category, and preview its colors live. Run it with:

    python -m cozy_tui.themes

Up/Down move the cursor, Right/Left expand/collapse a category, Enter/Space
(or a click) picks a theme (or toggles a category open/closed). Ctrl+T
cycles to the next theme in flat Theme.MODES order, expanding whichever
category it lands in. "Preview toast" pops a toast in the theme's
info/success/warning/error color, rotating levels on each click. Esc quits.
"""

from cozy_tui import App, Style, Theme, get_theme
from cozy_tui.events import Key
from cozy_tui.widgets import Box, Button, Label, Tree

_ROLES = ("accent", "muted", "info", "success", "warning", "error")
_LEVELS = ("info", "success", "warning", "error")


def main() -> None:
    app = App(
        full=True, style=Style(fg="white", bg="black"), title="Cozy TUI Theme Showcase"
    )

    # box/preview share app.style (same object, not a copy): mutating
    # app.style once, in _refresh() below, recolors both automatically.
    box = Box(0, 0, "1x1", title="🎨 Theme Showcase", border="rounded", style=app.style)
    app.dock(box, "fill", margin=1)

    box.add(Label(2, 1, "Pick a theme (Ctrl+T cycles):", Style(styles=["bold"])))

    # Theme.CATEGORIES (cozy_tui/_presets.py) groups the ever-growing preset
    # list -- a Tree shows that grouping directly (category nodes you expand
    # to browse) instead of dumping all ~35 themes into one flat list.
    tree = Tree(2, 2, height=14, connectors=True)
    leaves = {}  # mode -> TreeNode, for jumping to a theme programmatically
    active_category = None
    for category, modes in Theme.CATEGORIES.items():
        cat_node = tree.add(category)
        for mode in modes:
            leaf = cat_node.add(mode.title())
            leaf.metadata = mode
            leaves[mode] = leaf
            if mode == get_theme().mode:
                active_category = cat_node
    # Only the category the active theme lives in starts open, so the
    # overview stays compact (the actual point of grouping them) while still
    # landing on the current theme rather than a collapsed, invisible node.
    if active_category is not None:
        active_category.expand()
    box.add(tree)

    preview = Box(32, 0, "420x220", title="Preview", border="rounded", style=app.style)
    box.add(preview)

    preview.add(Label(2, 1, "Color roles:", Style(styles=["bold"])))
    swatches = {}
    for i, role in enumerate(_ROLES):
        row = 2 + i
        preview.add(Label(2, row, f"{role:<9}"))
        swatch = Label(12, row, "", Style())
        preview.add(swatch)
        swatches[role] = swatch

    selection_row = Label(12, 3 + len(_ROLES), "  Focused row preview  ", Style())
    preview.add(Label(2, 3 + len(_ROLES), "selection:"))
    preview.add(selection_row)

    status = Label(2, 5 + len(_ROLES), "", Style(fg="bright_black"))
    preview.add(status)

    def _refresh() -> None:
        theme = get_theme()
        for role, swatch in swatches.items():
            color = getattr(theme, role)
            swatch.text = f"██████  {color}"
            swatch.style = Style(fg=color)
        selection_row.style = theme.selection_style()
        app.style.fg = theme.style.fg
        app.style.bg = theme.style.bg  # already carries Style's "_bg" suffix
        status.text = f"active theme: {theme.mode}  ({len(Theme.MODES)} total)"
        app.invalidate()

    def _apply(mode) -> None:
        Theme(mode=mode).activate()
        leaf = leaves[mode]
        leaf.parent.expand()  # jumping here (e.g. via Ctrl+T) must reveal it
        vis = tree._visible()
        idx = tree._index_of(leaf, vis)
        if idx is not None:
            tree._index = idx
            tree._clamp(len(vis))
        _refresh()

    def _on_select(node) -> None:
        if node.is_leaf:  # a category node toggling open/closed isn't a pick
            _apply(node.metadata)

    tree.on_select(_on_select)
    _refresh()

    def _cycle() -> None:
        modes = Theme.MODES
        idx = modes.index(get_theme().mode)
        _apply(modes[(idx + 1) % len(modes)])

    app.on_key(Key.CTRL_T, _cycle, description="Cycle theme", section="App")

    toast_state = {"i": 0}

    def _preview_toast(_b) -> None:
        level = _LEVELS[toast_state["i"] % len(_LEVELS)]
        toast_state["i"] += 1
        app.toast(f"This is a {level} toast.", level=level)

    preview.add(Button(2, 6 + len(_ROLES), "Preview toast").on_click(_preview_toast))

    app.focus(tree)
    app.on_key(Key.ESC, lambda: "quit")
    app.run()


if __name__ == "__main__":
    main()
