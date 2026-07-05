"""Kanban Board — a keyboard-driven To Do / Doing / Done board.

Tab switches columns, Up/Down selects a card, Left/Right moves the selected card
between columns, Enter/`r` renames it, `a` adds a card, `d` deletes one, `c`
clears the board (with a confirm dialog), `?` shows help. Shows off:
  * multi-column layout built from Boxes + ListViews,
  * moving/renaming data via the public ListView API,
  * overlays: a text-entry prompt, a help panel, and a confirm modal.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Style
from cozy_tui.events import Key
from cozy_tui.widgets import Box, Button, Label, ListView

COLUMNS = ["To Do", "Doing", "Done"]
SEED = {
    "To Do": ["Design overlay API", "Write docs", "Add RadioGroup", "Ship 1.0"],
    "Doing": ["Retrofit Dropdown", "Wide-char tests"],
    "Done": ["Cross-platform backend", "Built-in clipboard"],
}


def main():
    app = App(full=True, style=Style(fg="white", bg="black"))

    header = Label(
        2,
        0,
        "KANBAN  Tab: column  ←/→: move  Enter/r: rename  a: add  d: delete  c: clear  ?: help  Esc: quit",
        Style(fg="bright_cyan", styles=["bold"]),
    )
    app.add(header)

    colw = max(16, (app.cols - 8) // 3)
    colh = max(8, app.rows - 4)
    lists: list[ListView] = []
    for i, name in enumerate(COLUMNS):
        x = 2 + i * (colw + 1)
        box = Box(x, 2, f"{colw * 10}x{colh * 10}", title=name, border="rounded")
        lv = ListView(1, 1, list(SEED[name]), width=colw - 2, height=colh - 2)
        box.add(lv)
        app.add(box)
        lists.append(lv)

    app.focus(lists[0])
    card_counter = [sum(len(v) for v in SEED.values())]

    def start_rename():
        ci = focused_column()
        if ci is None:
            return
        lv = lists[ci]
        idx = lv.selected_index
        if idx is None:
            return

        def submit(text):
            text = text.strip()
            if text:
                lv.set_item(idx, text)

        app.prompt("Rename card", str(lv.selected), on_submit=submit)

    def focused_column():
        try:
            return lists.index(app.focused)
        except ValueError:
            return None

    def move(delta):
        ci = focused_column()
        if ci is None:
            return
        src = lists[ci]
        card = src.selected
        target = ci + delta
        if card is None or not (0 <= target < len(lists)):
            return
        src.remove(card)
        lists[target].append(card)
        app.focus(lists[target])
        lists[target].set(card)  # keep the moved card selected

    def add_card():
        ci = focused_column()
        if ci is None:
            return
        card_counter[0] += 1
        name = f"New card {card_counter[0]}"  # unique, so set() lands on it
        lists[ci].append(name)
        lists[ci].set(name)
        start_rename()  # immediately let the user name it

    def delete_card():
        ci = focused_column()
        if ci is not None and lists[ci].selected is not None:
            lists[ci].remove(lists[ci].selected)

    def show_help():
        panel = Box(0, 0, "440x160", title="Help", border="rounded")
        rows = [
            "Tab / Shift+Tab   switch between columns",
            "Up / Down         select a card",
            "Left / Right      move the selected card",
            "a                 add a card",
            "d                 delete the selected card",
            "c                 clear the whole board",
            "Esc               quit",
        ]
        for r, text in enumerate(rows):
            panel.add(Label(2, 1 + r, text))
        panel.add(
            Button(2, 2 + len(rows), "Close").on_click(
                lambda b: app.close_overlay(panel)
            )
        )
        app.open_overlay(panel, close_on_click_outside=True)

    def confirm_clear():
        dlg = Box(0, 0, "380x110", title="Clear board?", border="rounded")
        dlg.add(Label(2, 1, "Remove every card from all columns?"))

        def do_clear(_b):
            for lv in lists:
                lv.clear()
            app.close_overlay(dlg)

        dlg.add(Button(2, 3, "Cancel").on_click(lambda b: app.close_overlay(dlg)))
        dlg.add(
            Button(13, 3, "Clear", style=Style(fg="white", bg="red")).on_click(do_clear)
        )
        app.open_overlay(dlg)

    for lv in lists:
        lv.on_select(lambda _val: start_rename())  # Enter on a card renames it

    app.on_key(Key.LEFT, lambda: move(-1))
    app.on_key(Key.RIGHT, lambda: move(1))
    app.on_key("r", start_rename)
    app.on_key("a", add_card)
    app.on_key("d", delete_card)
    app.on_key("c", confirm_clear)
    app.on_key("?", show_help)
    app.on_key(Key.ESC, lambda: "quit")
    app.on_key("q", lambda: "quit")
    app.run()


if __name__ == "__main__":
    main()
