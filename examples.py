import time

from cozy_tui import Input
from cozy_tui.widget import Widget
from cozy_tui.style import Style
from cozy_tui.widgets.box import Box
from cozy_tui.widgets.label import Label
from cozy_tui.app import App
from cozy_tui.events import Key


class CountdownTimer(Widget):
    def __init__(self, x, y, width, style=None):
        super().__init__(x, y, style)

        self.width = width
        self.minutes = 0
        self.remaining = 0
        self.running = False
        self._last = None

    def natural_width(self, scale):
        return self.width

    def _tick(self):
        now = time.monotonic()
        if self.running:
            if self._last is not None:
                self.remaining = max(0.0, self.remaining - (now - self._last))
            self._last = now
            if self.remaining == 0.0:
                self.running = False
                self._last = None

    def toggle(self):
        if self.remaining == 0.0:
            return
        self.running = not self.running
        self._last = time.monotonic() if self.running else None

    def reset(self):
        self.running = False
        self.remaining = float(self.minutes)
        self._last = None

    def draw(self, canvas):
        self._tick()
        w = self.width
        m, s = divmod(int(self.remaining), 60)

        # Time display
        time_str = f"{m:02d}:{s:02d}"
        if self.remaining == 0.0:
            t_style = Style(fg="green", styles=["bold"])
        elif self.running:
            t_style = Style(fg="bright_white", styles=["bold"])
        else:
            t_style = Style(fg="yellow", styles=["bold"])
        canvas.write(self.abs_x, self.abs_y, time_str.center(w), t_style)

        # Progress bar
        if self.minutes == 0:
            frac = 0
        else:
            frac = self.remaining / self.minutes
        bar_w = w - 2
        filled = round(frac * bar_w)
        bar = "█" * filled + "░" * (bar_w - filled)
        canvas.write(self.abs_x, self.abs_y + 2, f"[{bar}]", self.style)

        # Status
        if self.remaining == 0.0:
            status, fg = "✓  Time's up!", "green"
        elif self.running:
            status, fg = "▶  Running...", "bright_green"
        elif self.remaining < self.minutes:
            status, fg = "⏸  Paused", "yellow"
        else:
            status, fg = "●  Ready", "cyan"
        canvas.write(self.abs_x, self.abs_y + 4, status.center(w), Style(fg=fg))

    def set_minutes(self, minutes):
        self.minutes = minutes * 60
        self.remaining = self.minutes
        self.running = False
        self._last = None


app = App("1200x900", style=Style(fg="white", bg="black"), full=True)

frame = Box(
    2,
    1,
    "1020x420",
    border="rounded",
    style=Style(fg="cyan", bg="black", styles=["bold"]),
    title="COUNTDOWN TIMER",
)


minutes_input = Input(3, 2, 30, placeholder="How many minutes you want")

timer = CountdownTimer(3, 3, width=30, style=Style(fg="cyan", bg="black"))
frame.add(timer)
frame.add(minutes_input)

frame.add(Label("─" * 30, 3, 8, style=Style(fg="cyan")))
frame.add(Label("SPACE  Start / Pause", 3, 9, style=Style(fg="white")))
frame.add(Label("R      Reset", 3, 10, style=Style(fg="white")))
frame.add(Label("ESC    Quit", 3, 11, style=Style(fg="white")))
app.add(frame)

app.focus(minutes_input)


def start():
    text = minutes_input.get()

    if not text:
        return

    timer.set_minutes(int(text))
    timer.toggle()


app.on_key(" ", timer.toggle)
app.on_key(Key.ENTER, start)
app.on_key("r", timer.reset)
app.on_key("R", timer.reset)
app.on_key(Key.ESC, lambda: "quit")

app.run()
