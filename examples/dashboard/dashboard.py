"""Dashboard — one app showcasing Tabs, ScrollView, ProgressBar, Spinner, and toasts.

A mock "download manager":

  * Tabs          — organise the app into Downloads / Activity / About panels.
  * ProgressBar   — a bar per file, advanced by an ``app.every`` timer.
  * Spinner       — shown next to "Start" while downloads are in flight.
  * ScrollView    — the Activity log (autoscroll keeps the newest line in view).
  * app.toast(…)  — a notification as each file finishes, and when all are done.

    python examples/dashboard/dashboard.py

Tab moves focus (start on the tab strip; Tab again dives into a panel), ←/→ or
click switch tabs, Enter/Space activate, Esc quits.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Style
from cozy_tui.events import Key
from cozy_tui.widgets import Box, Button, Label, ProgressBar, ScrollView, Spinner, Tabs

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

    header = Box(0, 0, "10x10", title="⬇ Cozy Downloader", border="rounded", style=BG)
    header.add(Label(1, 1, "Tabs · ScrollView · ProgressBar · Spinner · toasts", MUTED))
    app.dock(header, "top")

    footer = Box(0, 0, "10x10", title="keys", border="rounded", style=BG)
    hint = Label(1, 1, "Tab: focus · ←/→: switch tab · Enter: Start · Esc: quit", MUTED)
    footer.add(hint)
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

    start_row = 2 + len(FILES)
    spinner = Spinner(12, start_row, label="downloading…")
    state = {"running": False, "timer": None, "log_n": 0}

    # ── Activity tab: an autoscrolling log ──────────────────────────────────────
    activity_panel.add(Label(1, 0, "Activity log", ACCENT))
    log = ScrollView(1, 1, "760x130", autoscroll=True, style=Style(bg="rgb(18,20,26)"))
    activity_panel.add(log)

    def add_log(text, color="white"):
        stamp = time.strftime("%H:%M:%S")
        log.add(Label(0, state["log_n"], f"{stamp}  {text}", Style(fg=color)))
        state["log_n"] += 1

    # ── About tab ───────────────────────────────────────────────────────────────
    about_panel.add(Label(1, 0, "Cozy Dashboard", ACCENT))
    about_panel.add(Label(1, 2, "One example wiring together several widgets:"))
    for i, line in enumerate(
        [
            "Tabs        — the three panels above",
            "ProgressBar — one bar per file on the Downloads tab",
            "Spinner     — spins next to Start while work is in flight",
            "ScrollView  — the Activity log (autoscroll + scrollbar)",
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
        if spinner in downloads_panel.children:
            downloads_panel.children.remove(spinner)
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
        if all(d["done"] for d in downloads):
            finish()

    def start(_b):
        if state["running"]:
            return
        if all(d["done"] for d in downloads):  # restart a finished batch
            for d in downloads:
                d["done"] = False
                d["bar"].set(0)
        state["running"] = True
        if spinner not in downloads_panel.children:
            downloads_panel.add(spinner)
        add_log("started downloads", "bright_cyan")
        app.toast(f"Starting {len(downloads)} downloads…", level="info")
        state["timer"] = app.every(0.12, tick)

    downloads_panel.add(Button(1, start_row, "Start").on_click(start))

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
