"""Dashboard — one app showcasing Tabs, Log, ProgressBar, Spinner, and toasts.

A mock "download manager":

  * Tabs          — organise the app into Downloads / Activity / About panels.
  * ProgressBar   — a bar per file, advanced by an ``app.every`` timer.
  * Spinner       — shown next to "Start" while downloads are in flight.
  * Log           — the Activity log: append strings, it owns the rows, keeps
                    the newest line in view, and caps its own history. Its
                    ``markup=True`` colors the timestamp inside each line.
  * app.toast(…)  — a notification as each file finishes, and when all are done.

    python examples/dashboard/dashboard.py

Tab moves focus (start on the tab strip; Tab again dives into a panel), ←/→ or
click switch tabs, Enter/Space activate, Esc quits.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, State, Style
from cozy_tui.events import Key
from cozy_tui.widgets import Box, Button, HBox, Label, Log, ProgressBar, Spinner, Tabs

ACCENT = Style(fg="bright_cyan")
MUTED = Style(fg="bright_black")
BG = Style(fg="white", bg="rgb(24,26,32)")

# (filename, percent added per tick) — different speeds so they finish staggered
FILES = [
    ("ubuntu-24.04.iso", 3.1),
    ("family-photos.zip", 5.7),
    ("holiday-movie.mkv", 2.3),
    ("dataset.csv", 8.4),
]


def main():
    app = App(full=True, style=BG, title="Cozy Dashboard")

    # The header's content is an HBox filling the box, split by `justify`: a
    # description on the left, a live "N / N downloaded" status on the right. The
    # status is a State (see the footer) — this Label is bound to it and repaints
    # itself whenever the download loop sets it.
    status = State(f"0 / {len(FILES)} downloaded")
    header = Box(0, 0, "10x10", title="⬇ Cozy Downloader", border="rounded", style=BG)
    header_bar = HBox(0, 0, align="center", justify="between", padding=(0, 1))
    header_bar.add(Label(0, 0, "Tabs · Log · ProgressBar · Spinner · toasts", MUTED))
    header_bar.add(Label(0, 0, status, ACCENT))
    header.dock(header_bar, "fill")
    app.dock(header, "top")

    # The footer's content is likewise a filled HBox split by `justify`: the key
    # hints on the left, the controls (a spinner + Start) on the right, kept on
    # one line by `align="center"`. The spinner is only `visible` while a batch
    # runs — a hidden child collapses its own gap, so Start slides left to meet
    # the edge when there's no spinner.
    footer = Box(0, 0, "10x10", title="keys", border="rounded", style=BG)
    spinner = Spinner(0, 0, label="downloading…")
    spinner.visible = False
    start_btn = Button(0, 0, "Start")
    controls = HBox(0, 0, gap=2, align="center")
    controls.add(spinner)
    controls.add(start_btn)
    hint = Label(0, 0, "Tab: focus · ←/→: switch tab · Enter: Start · Esc: quit", MUTED)
    footer_bar = HBox(0, 0, gap=2, align="center", justify="between", padding=(0, 1))
    footer_bar.add(hint)
    footer_bar.add(controls)
    footer.dock(footer_bar, "fill")
    app.dock(footer, "bottom")

    tabs = Tabs(0, 0, "10x10", accent="bright_cyan")
    downloads_panel = tabs.add_tab("Downloads")
    activity_panel = tabs.add_tab("Activity")
    about_panel = tabs.add_tab("About")
    app.dock(tabs, "fill")

    # ── Downloads tab: a ProgressBar per file + a Start button/Spinner ──────────
    downloads_panel.add(Label(1, 0, "Files", ACCENT))
    downloads = []
    for i, (name, speed) in enumerate(FILES):
        row = 1 + i
        downloads_panel.add(Label(1, row, name))
        bar = ProgressBar(20, row, fill="█", empty="░", width=36, style=ACCENT)
        downloads_panel.add(bar)
        downloads.append({"name": name, "bar": bar, "speed": speed, "done": False})

    state = {"running": False, "timer": None}

    # ── Activity tab: a Log ─────────────────────────────────────────────────────
    # Log owns its rows, its autoscroll, and its history cap, so the app only
    # ever hands it a string. markup=True colors *within* a line: the timestamp
    # stays grey while the message takes the event's own color.
    activity_panel.add(Label(1, 0, "Activity log", ACCENT))
    log = Log(
        1, 1, "760x130", markup=True, max_lines=500, style=Style(bg="rgb(18,20,26)")
    )
    activity_panel.add(log)

    def add_log(text, color="white"):
        stamp = time.strftime("%H:%M:%S")
        log.log(f"[bright_black]{stamp}[/]  [{color}]{text}[/]")

    # ── About tab ───────────────────────────────────────────────────────────────
    about_panel.add(Label(1, 0, "Cozy Dashboard", ACCENT))
    about_panel.add(Label(1, 2, "One example wiring together several widgets:"))
    for i, line in enumerate(
        [
            "Tabs        — the three panels above",
            "ProgressBar — one bar per file on the Downloads tab",
            "Spinner     — spins next to Start while work is in flight",
            "Log         — the Activity log (autoscroll + scrollbar + markup)",
            "app.toast   — pops when each file (and the batch) completes",
        ]
    ):
        about_panel.add(Label(3, 4 + i, line, MUTED))

    # ── the download loop (main-thread timer) ───────────────────────────────────
    def finish():
        if state["timer"] is not None:
            app.cancel(state["timer"])
            state["timer"] = None
        state["running"] = False
        spinner.visible = False
        add_log("all downloads complete", "bright_green")
        app.toast("All downloads complete 🎉", level="success")

    def tick():
        for d in downloads:
            if d["done"]:
                continue
            value = min(100, d["bar"].get() + d["speed"])
            d["bar"].set(value)
            if value >= 100:
                d["done"] = True
                add_log(f"completed {d['name']}", "bright_green")
                app.toast(f"{d['name']} finished", level="success")
        status.set(f"{sum(d['done'] for d in downloads)} / {len(downloads)} downloaded")
        if all(d["done"] for d in downloads):
            finish()

    def start(_b):
        if state["running"]:
            return
        if all(d["done"] for d in downloads):  # restart a finished batch
            for d in downloads:
                d["done"] = False
                d["bar"].set(0)
            status.set(f"0 / {len(downloads)} downloaded")
        state["running"] = True
        spinner.visible = True
        add_log("started downloads", "bright_cyan")
        app.toast(f"Starting {len(downloads)} downloads…", level="info")
        state["timer"] = app.every(0.12, tick)

    start_btn.on_click(start)

    def on_tab(index):
        hint.text = {
            0: "Tab: into files · Enter on Start · ←/→: switch tab · Esc: quit",
            1: "Wheel / ↑↓ / PgUp-Dn scroll the log · ←/→: switch tab · Esc: quit",
            2: "←/→: switch tab · Esc: quit",
        }[index]

    tabs.on_change(on_tab)
    on_tab(0)

    app.focus(tabs.bar)
    app.on_key(Key.ESC, lambda: "quit")
    app.run()


if __name__ == "__main__":
    main()
