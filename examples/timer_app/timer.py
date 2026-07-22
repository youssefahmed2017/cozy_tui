import json
import os
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Style
from cozy_tui.events import Key
from cozy_tui.widget import Widget
from cozy_tui.widgets import Box, Button, HBox, Input, Label, ProgressBar

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
        self._bar = ProgressBar(
            x,
            y + 2,
            progress=0,
            width=width,
            style=style or Style(fg="cyan", bg="black"),
        )

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
        self._bar.x = self.abs_x
        self._bar.y = self.abs_y + 2
        self._bar._layout_y = 0
        self._bar.set(round(frac * 100))
        self._bar.draw(canvas)

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
# App & screens
#
# Each screen is built **once**, here, and refilled on the way in rather than
# rebuilt on every switch. That's what keeps a half-typed username around when
# you bounce to the welcome screen and back, and it's why the error line is a
# hidden Label (`visible`) rather than a widget that only exists on the retry.
# ─────────────────────────────────────────────────────────────────────────────

data = load_data()
current_user = [None]

app = App(full=True, size=None, style=Style(fg="white", bg="black"))

welcome = app.screen("welcome")
login = app.screen("login")
register = app.screen("register")
timer_screen = app.screen("timer")

MUTED = Style(fg="bright_black")
ERROR = Style(fg="red")


def show_error(label, message):
    label.text = f"✗  {message}"
    label.visible = True


def clear_error(label):
    label.visible = False


def credentials_form(screen, title, color, action_label, action, hints):
    """Build the login/register screen — they differ only in wording and in what
    the action button does, so one builder covers both. Returns the two Inputs
    and the error Label so the caller's handler can read and write them."""
    box = Box(
        2, 1, "900x390", border="rounded", style=Style(fg=color, bg="black"), title=title
    )
    inp_user = Input(13, 2, 22, placeholder=hints[0])
    inp_pass = Input(13, 4, 22, placeholder=hints[1], masked=True)
    box.add(Label(3, 2, "Username:"))
    box.add(inp_user)
    box.add(Label(3, 4, "Password:"))
    box.add(inp_pass)

    # Built once and hidden, not added on the retry: a hidden widget takes no
    # space and can't be Tabbed into, so this reads exactly like not being
    # there — without rebuilding the screen (and losing what was typed) to
    # show a message.
    error = Label(3, 6, "", style=ERROR)
    error.visible = False
    box.add(error)

    row = HBox(3, 8, gap=2)
    btn_go = Button(0, 0, action_label, width=14, style=Style(fg="white", bg=color))
    btn_back = Button(0, 0, "Back", width=12, style=Style(fg="white", bg="bright_black"))
    btn_go.on_click(lambda _b: action())
    btn_back.on_click(lambda _b: app.show(welcome))
    row.add(btn_go).add(btn_back)
    box.add(row)

    screen.add(box)
    screen.focus(inp_user)
    # Per-screen binding: Esc means "back" here and "quit" on the welcome
    # screen, with no dispatcher in the middle asking which screen is current.
    screen.on_key(Key.ESC, lambda: app.show(welcome))
    return inp_user, inp_pass, error


# ── welcome ──────────────────────────────────────────────────────────────────

welcome_box = Box(
    2,
    1,
    "900x270",
    border="rounded",
    style=Style(fg="cyan", bg="black"),
    title=" TIMER APP ",
)
welcome_box.add(Label(3, 2, "Welcome! Log in or register to track your timers."))

_row = HBox(3, 5, gap=3)
_btn_login = Button(0, 0, "Login", width=14, style=Style(fg="white", bg="blue"))
_btn_reg = Button(0, 0, "Register", width=14, style=Style(fg="white", bg="green"))
_btn_quit = Button(0, 0, "Quit", width=14, style=Style(fg="white", bg="red"))
_btn_login.on_click(lambda _b: app.show(login))
_btn_reg.on_click(lambda _b: app.show(register))
_btn_quit.on_click(lambda _b: app.quit())
_row.add(_btn_login).add(_btn_reg).add(_btn_quit)
welcome_box.add(_row)

welcome.add(welcome_box)
welcome.focus(_btn_login)
welcome.on_key(Key.ESC, app.quit, description="Quit", section="Actions")


# ── login ────────────────────────────────────────────────────────────────────


def do_login():
    user, password = login_user.value.strip(), login_pass.value.strip()
    if not user or not password:
        return show_error(login_error, "Please fill in both fields.")
    users = data.get("users", {})
    if user not in users:
        return show_error(login_error, "Account not found. Register first.")
    if users[user]["password"] != password:
        return show_error(login_error, "Incorrect password.")
    current_user[0] = user
    app.show(timer_screen)


login_user, login_pass, login_error = credentials_form(
    login, " LOGIN ", "blue", "Login", do_login, ("your username", "your password")
)
login.on_show(lambda _s: clear_error(login_error))


# ── register ─────────────────────────────────────────────────────────────────


def do_register():
    user, password = reg_user.value.strip(), reg_pass.value.strip()
    if not user or not password:
        return show_error(reg_error, "Please fill in both fields.")
    users = data.setdefault("users", {})
    if user in users:
        return show_error(reg_error, f"Username '{user}' is already taken.")
    users[user] = {"password": password, "records": []}
    save_data()
    current_user[0] = user
    app.show(timer_screen)


reg_user, reg_pass, reg_error = credentials_form(
    register,
    " REGISTER ",
    "green",
    "Register",
    do_register,
    ("choose a username", "choose a password"),
)
register.on_show(lambda _s: clear_error(reg_error))


# ── timer ────────────────────────────────────────────────────────────────────

timer_box = Box(
    2,
    1,
    "1020x630",
    border="rounded",
    style=Style(fg="cyan", bg="black"),
    title=" TIMER ",
)

countdown = CountdownTimer(3, 2, width=30, style=Style(fg="cyan", bg="black"))
timer_box.add(countdown)
timer_box.add(Label(3, 8, "─" * 30, style=Style(fg="cyan")))

inp_minutes = Input(12, 9, 8, placeholder="e.g. 5")
timer_box.add(Label(3, 9, "Minutes:"))
timer_box.add(inp_minutes)
minutes_error = Label(21, 9, "", style=ERROR)
minutes_error.visible = False
timer_box.add(minutes_error)

_ctrl = HBox(3, 11, gap=2)
btn_set = Button(0, 0, "Set & Start", width=14, style=Style(fg="white", bg="blue"))
_btn_pause = Button(0, 0, "Pause/Resume", width=15, style=Style(fg="white", bg="yellow"))
_btn_reset = Button(0, 0, "Reset", width=10, style=Style(fg="white", bg="bright_black"))
_btn_pause.on_click(lambda _b: countdown.toggle())
_btn_reset.on_click(lambda _b: countdown.reset())
_ctrl.add(btn_set).add(_btn_pause).add(_btn_reset)
timer_box.add(_ctrl)

timer_box.add(Label(3, 13, "─" * 30, style=Style(fg="cyan")))
timer_box.add(
    Label(3, 14, "Recent Records", style=Style(fg="bright_white", styles=["bold"]))
)

# Five fixed slots, filled by refresh_records(). Fixed rather than add()-ed per
# record so switching users never rebuilds the layout — an unused slot just
# goes `visible = False`, and nothing below it moves.
record_labels = [Label(4, 15 + i, "", style=MUTED) for i in range(5)]
for _label in record_labels:
    timer_box.add(_label)
no_records = Label(4, 15, "No records yet.", style=MUTED)
timer_box.add(no_records)

timer_box.add(Label(3, 21, "─" * 30, style=Style(fg="cyan")))
_btn_logout = Button(3, 22, "Logout", width=12, style=Style(fg="white", bg="magenta"))
_btn_logout.on_click(lambda _b: logout())
timer_box.add(_btn_logout)
timer_box.add(Label(17, 22, "SPACE Pause  R Reset  ESC Quit", style=MUTED))

timer_screen.add(timer_box)
timer_screen.focus(inp_minutes)


def records():
    return data["users"][current_user[0]].setdefault("records", [])


def refresh_records(_screen=None):
    """Refill the timer screen for whoever just logged in. Runs from on_show,
    so a different user's records appear without anything being rebuilt."""
    timer_box.title = f" TIMER — {current_user[0]} "
    recent = records()[-5:][::-1]  # last 5, newest first
    no_records.visible = not recent
    for i, label in enumerate(record_labels):
        label.visible = i < len(recent)
        if label.visible:
            record = recent[i]
            label.text = f"{record['date']}  —  {record['minutes']} min"


def on_complete(original_minutes):
    records().append({"minutes": original_minutes, "date": date.today().isoformat()})
    save_data()
    refresh_records()


countdown.on_complete(on_complete)


def minutes_valid() -> bool:
    text = inp_minutes.value.strip()
    return text.isdigit() and int(text) > 0


def do_set(_b=None):
    if minutes_valid():
        clear_error(minutes_error)
        countdown.set_minutes(int(inp_minutes.value.strip()))
        countdown.toggle()


# `disabled` rather than a silent no-op click: the button greys itself out, so
# it's obvious *before* pressing it that there's nothing to start.
def sync_set_button(_text=None):
    btn_set.disabled = not minutes_valid()


inp_minutes.on_change(sync_set_button)

# on_blur, not on_change: "5" isn't an error just because you haven't typed the
# "0" of "50" yet. The message waits until you're done with the field.
inp_minutes.on_blur(
    lambda w: (
        show_error(minutes_error, "Whole minutes, please.")
        if w.value.strip() and not minutes_valid()
        else clear_error(minutes_error)
    )
)
btn_set.on_click(do_set)
sync_set_button()


def logout():
    current_user[0] = None
    countdown.reset()
    app.show(welcome)


timer_screen.on_show(refresh_records)
timer_screen.on_key(Key.SPACE, lambda: countdown.toggle(), description="Pause/resume")
timer_screen.on_key("r", lambda: countdown.reset(), description="Reset")
timer_screen.on_key("R", lambda: countdown.reset())
timer_screen.on_key(Key.ESC, app.quit, description="Quit", section="Actions")


# ─────────────────────────────────────────────────────────────────────────────

app.show(welcome)
app.run()
