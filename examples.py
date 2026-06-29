import json
import os
import sys
import time
from datetime import date

from cozy_tui import App, Box, Label, Input, Button, HBox, Style
from cozy_tui.widget import Widget
from cozy_tui.events import Key

# ─────────────────────────────────────────────────────────────────────────────
# Data layer
# ─────────────────────────────────────────────────────────────────────────────

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timer_data.json")


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"users": {}}


def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# CountdownTimer widget
# ─────────────────────────────────────────────────────────────────────────────


class CountdownTimer(Widget):
    def __init__(self, x, y, width, style=None):
        super().__init__(x, y, style)
        self.width = width
        self.minutes = 0  # stored in seconds
        self.remaining = 0.0
        self.running = False
        self._last = None
        self._complete_cb = None

    def natural_width(self, scale):
        return self.width

    def natural_height(self, scale):
        return 5

    def on_complete(self, func):
        """Callback receives original duration in minutes when timer hits 0."""
        self._complete_cb = func
        return self

    def _tick(self):
        if not self.running:
            return
        now = time.monotonic()
        if self._last is not None:
            self.remaining = max(0.0, self.remaining - (now - self._last))
        self._last = now
        if self.remaining == 0.0:
            self.running = False
            self._last = None
            if self._complete_cb:
                self._complete_cb(self.minutes // 60)

    def toggle(self):
        if self.remaining == 0.0:
            return
        self.running = not self.running
        self._last = time.monotonic() if self.running else None

    def reset(self):
        self.running = False
        self.remaining = float(self.minutes)
        self._last = None

    def set_minutes(self, m):
        self.minutes = m * 60
        self.remaining = float(self.minutes)
        self.running = False
        self._last = None

    def draw(self, canvas):
        self._tick()
        w = self.width
        m, s = divmod(int(self.remaining), 60)

        if self.remaining == 0.0 and self.minutes > 0:
            t_style = Style(fg="green", styles=["bold"])
        elif self.running:
            t_style = Style(fg="bright_white", styles=["bold"])
        else:
            t_style = Style(fg="yellow", styles=["bold"])
        canvas.write(self.abs_x, self.abs_y, f"{m:02d}:{s:02d}".center(w), t_style)

        frac = (self.remaining / self.minutes) if self.minutes else 0
        bar_w = w - 2
        filled = round(frac * bar_w)
        bar = "█" * filled + "░" * (bar_w - filled)
        canvas.write(self.abs_x, self.abs_y + 2, f"[{bar}]", self.style)

        if self.remaining == 0.0 and self.minutes > 0:
            status, fg = "✓  Time's up!", "green"
        elif self.running:
            status, fg = "▶  Running...", "bright_green"
        elif self.minutes > 0:
            status, fg = "⏸  Paused", "yellow"
        else:
            status, fg = "●  Ready", "cyan"
        canvas.write(self.abs_x, self.abs_y + 4, status.center(w), Style(fg=fg))


# ─────────────────────────────────────────────────────────────────────────────
# App & global state
# ─────────────────────────────────────────────────────────────────────────────

data = load_data()
current_user = [None]

app = App(full=True, size=None, style=Style(fg="white", bg="black"))


def switch_screen(box, focus=None, keys=None):
    """Replace the current screen with a new box and key bindings."""
    app.widgets = [box]
    app.focused = focus
    app._key_handlers = dict(keys or {})
    app.invalidate()


# ─────────────────────────────────────────────────────────────────────────────
# Welcome screen
# ─────────────────────────────────────────────────────────────────────────────


def show_welcome():
    box = Box(
        2,
        1,
        "900x270",
        border="rounded",
        style=Style(fg="cyan", bg="black"),
        title=" TIMER APP ",
    )

    box.add(Label(3, 2, "Welcome! Log in or register to track your timers."))

    row = HBox(3, 5, gap=3)
    btn_l = Button(0, 0, "Login", width=14, style=Style(fg="white", bg="blue"))
    btn_r = Button(0, 0, "Register", width=14, style=Style(fg="white", bg="green"))
    btn_q = Button(0, 0, "Quit", width=14, style=Style(fg="white", bg="red"))

    btn_l.on_click(lambda b: show_login())
    btn_r.on_click(lambda b: show_register())
    btn_q.on_click(lambda b: sys.exit(0))

    row.add(btn_l).add(btn_r).add(btn_q)
    box.add(row)

    switch_screen(box, focus=btn_l, keys={Key.ESC: lambda: "quit"})


# ─────────────────────────────────────────────────────────────────────────────
# Login screen
# ─────────────────────────────────────────────────────────────────────────────


def show_login(error=""):
    box = Box(
        2,
        1,
        "900x390",
        border="rounded",
        style=Style(fg="blue", bg="black"),
        title=" LOGIN ",
    )

    inp_user = Input(13, 2, 22, placeholder="your username")
    inp_pass = Input(13, 4, 22, placeholder="your password", masked=True)

    box.add(Label(3, 2, "Username:"))
    box.add(inp_user)
    box.add(Label(3, 4, "Password:"))
    box.add(inp_pass)

    if error:
        box.add(Label(3, 6, f"✗  {error}", style=Style(fg="red")))

    row = HBox(3, 8, gap=2)
    btn_login = Button(0, 0, "Login", width=12, style=Style(fg="white", bg="blue"))
    btn_back = Button(
        0, 0, "Back", width=12, style=Style(fg="white", bg="bright_black")
    )

    def do_login(b):
        u = inp_user.value.strip()
        p = inp_pass.value.strip()
        if not u or not p:
            show_login("Please fill in both fields.")
            return
        users = data.get("users", {})
        if u not in users:
            show_login("Account not found. Register first.")
            return
        if users[u]["password"] != p:
            show_login("Incorrect password.")
            return
        current_user[0] = u
        show_timer()

    btn_login.on_click(do_login)
    btn_back.on_click(lambda b: show_welcome())
    row.add(btn_login).add(btn_back)
    box.add(row)

    switch_screen(box, focus=inp_user, keys={Key.ESC: lambda: show_welcome()})


# ─────────────────────────────────────────────────────────────────────────────
# Register screen
# ─────────────────────────────────────────────────────────────────────────────


def show_register(error=""):
    box = Box(
        2,
        1,
        "900x390",
        border="rounded",
        style=Style(fg="green", bg="black"),
        title=" REGISTER ",
    )

    inp_user = Input(13, 2, 22, placeholder="choose a username")
    inp_pass = Input(13, 4, 22, placeholder="choose a password", masked=True)

    box.add(Label(3, 2, "Username:"))
    box.add(inp_user)
    box.add(Label(3, 4, "Password:"))
    box.add(inp_pass)

    if error:
        box.add(Label(3, 6, f"✗  {error}", style=Style(fg="red")))

    row = HBox(3, 8, gap=2)
    btn_reg = Button(0, 0, "Register", width=14, style=Style(fg="white", bg="green"))
    btn_back = Button(
        0, 0, "Back", width=14, style=Style(fg="white", bg="bright_black")
    )

    def do_register(b):
        u = inp_user.value.strip()
        p = inp_pass.value.strip()
        if not u or not p:
            show_register("Please fill in both fields.")
            return
        users = data.setdefault("users", {})
        if u in users:
            show_register(f"Username '{u}' is already taken.")
            return
        users[u] = {"password": p, "records": []}
        save_data()
        current_user[0] = u
        show_timer()

    btn_reg.on_click(do_register)
    btn_back.on_click(lambda b: show_welcome())
    row.add(btn_reg).add(btn_back)
    box.add(row)

    switch_screen(box, focus=inp_user, keys={Key.ESC: lambda: show_welcome()})


# ─────────────────────────────────────────────────────────────────────────────
# Timer screen
# ─────────────────────────────────────────────────────────────────────────────


def show_timer():
    username = current_user[0]
    user = data["users"][username]
    records = user.setdefault("records", [])

    box = Box(
        2,
        1,
        "1020x630",
        border="rounded",
        style=Style(fg="cyan", bg="black"),
        title=f" TIMER — {username} ",
    )

    timer = CountdownTimer(3, 2, width=30, style=Style(fg="cyan", bg="black"))

    def on_complete(orig_minutes):
        records.append({"minutes": orig_minutes, "date": date.today().isoformat()})
        save_data()
        show_timer()  # refresh so the new record appears

    timer.on_complete(on_complete)
    box.add(timer)

    box.add(Label(3, 8, "─" * 30, style=Style(fg="cyan")))

    inp_minutes = Input(12, 9, 8, placeholder="e.g. 5")
    box.add(Label(3, 9, "Minutes:"))
    box.add(inp_minutes)

    ctrl = HBox(3, 11, gap=2)
    btn_set = Button(0, 0, "Set & Start", width=14, style=Style(fg="white", bg="blue"))
    btn_pause = Button(
        0, 0, "Pause/Resume", width=15, style=Style(fg="white", bg="yellow")
    )
    btn_reset = Button(
        0, 0, "Reset", width=10, style=Style(fg="white", bg="bright_black")
    )

    def do_set(b):
        t = inp_minutes.value.strip()
        if t.isdigit() and int(t) > 0:
            timer.set_minutes(int(t))
            timer.toggle()

    btn_set.on_click(do_set)
    btn_pause.on_click(lambda b: timer.toggle())
    btn_reset.on_click(lambda b: timer.reset())
    ctrl.add(btn_set).add(btn_pause).add(btn_reset)
    box.add(ctrl)

    box.add(Label(3, 13, "─" * 30, style=Style(fg="cyan")))
    box.add(
        Label(3, 14, "Recent Records", style=Style(fg="bright_white", styles=["bold"]))
    )

    recent = records[-5:][::-1]  # last 5, newest first
    if recent:
        for i, rec in enumerate(recent):
            box.add(
                Label(
                    4,
                    15 + i,
                    f"{rec['date']}  —  {rec['minutes']} min",
                    style=Style(fg="bright_black"),
                )
            )
    else:
        box.add(Label(4, 15, "No records yet.", style=Style(fg="bright_black")))

    box.add(Label(3, 21, "─" * 30, style=Style(fg="cyan")))

    btn_logout = Button(
        3, 22, "Logout", width=12, style=Style(fg="white", bg="magenta")
    )
    btn_logout.on_click(lambda b: _logout())
    box.add(btn_logout)
    box.add(
        Label(17, 22, "SPACE Pause  R Reset  ESC Quit", style=Style(fg="bright_black"))
    )

    switch_screen(
        box,
        focus=inp_minutes,
        keys={
            " ": lambda: timer.toggle(),
            "r": lambda: timer.reset(),
            "R": lambda: timer.reset(),
            Key.ESC: lambda: "quit",
        },
    )


def _logout():
    current_user[0] = None
    show_welcome()


# ─────────────────────────────────────────────────────────────────────────────

show_welcome()
app.run()
