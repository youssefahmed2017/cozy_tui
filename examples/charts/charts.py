"""Live charts — a mock system monitor showing off Sparkline and BarChart.

  * Sparkline — a one-row CPU trend, fed a new sample every tick with `push()`,
    so the line scrolls left as history rolls off its fixed `width`.
  * BarChart  — memory per process, driven by a `State` the tick reassigns; the
    bars rescale themselves as the values drift. More processes than rows, so a
    `height=` cap turns it into a scrolling viewport (wheel / arrows / drag).

Both are plain-number widgets: no canvas, no dependency, just block glyphs.

    python examples/charts/charts.py

Space pauses/resumes the feed, Esc quits.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Key, State, Style
from cozy_tui.widgets import BarChart, Box, Label, Rule, Sparkline

ACCENT = Style(fg="bright_cyan")
MUTED = Style(fg="bright_black")

app = App(full=True, title="Cozy Monitor")

# ── CPU: a Sparkline fed one sample per tick ──────────────────────────────────
cpu_box = Box(2, 1, "560x90", title=" CPU ", border="rounded")
cpu_pct = State("0%")
cpu_box.add(Label(2, 1, cpu_pct, ACCENT))  # State-bound "current %" readout
# 48 cells wide → 48 samples of history; push() trims to that and scrolls left.
cpu_spark = Sparkline(2, 3, [], width=48, minimum=0, maximum=100, style=ACCENT)
cpu_box.add(cpu_spark)
app.add(cpu_box)

# ── Memory: a scrollable BarChart driven by a State ───────────────────────────
# More processes than fit the box, so `height=` caps it to a scrolling viewport:
# focus it and use the wheel / ↑↓ / PageUp-Down / Home-End, or drag the thumb.
mem_box = Box(2, 8, "560x150", title=" Memory by process ", border="rounded")
mem_box.add(Rule(1, 1, title="MB", style=MUTED))
PROCS = [
    "python", "chrome", "code", "docker", "postgres", "node", "firefox",
    "slack", "spotify", "ssh-agent", "systemd", "gnome-shell", "pipewire",
]  # fmt: skip
mem = State([(name, random.randint(200, 1400)) for name in PROCS])
mem_chart = BarChart(2, 3, mem, width=52, height=9)
mem_box.add(mem_chart)
app.add(mem_box)
app.focus(mem_chart)  # so the wheel / arrow keys scroll the chart

app.dock(Label(0, 0, "Space pauses · scroll the chart · Esc quits", MUTED), "bottom", margin=1)

_cpu = 30.0
running = [True]


def tick():
    if not running[0]:
        return
    global _cpu
    # a random walk that stays in [2, 98], so the line wanders like a real gauge
    _cpu = max(2.0, min(98.0, _cpu + random.uniform(-14, 14)))
    cpu_pct.set(f"{round(_cpu)}%")
    cpu_spark.push(_cpu)
    # nudge each process's memory a little; the bars rescale to the new max
    mem.set([(name, max(80, mb + random.randint(-90, 90))) for name, mb in mem.value])


app.every(0.2, tick)
app.on_key(Key.SPACE, lambda: running.__setitem__(0, not running[0]))
app.on_key(Key.ESC, app.quit)
app.run()
