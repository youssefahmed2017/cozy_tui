import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Style
from cozy_tui.widgets import Box, Button, CheckItem, CheckList, HBox, Input, Label
from cozy_tui.events import Key

# ── Data layer ────────────────────────────────────────────────────────────────

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "todo_data.json")


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


data = load_data()

# ── App & helpers ─────────────────────────────────────────────────────────────

app = App(full=True, style=Style(fg="white", bg="black"))
current_user = [None]


def switch_screen(box, focus=None, keys=None):
    app.widgets = [box]
    app.focused = focus
    app._key_handlers = dict(keys or {})
    app.invalidate()


# ── Welcome screen ────────────────────────────────────────────────────────────


def show_welcome():
    box = Box(
        2,
        1,
        "900x270",
        border="rounded",
        style=Style(fg="cyan", bg="black"),
        title=" TO-DO LIST ",
    )

    box.add(Label(3, 2, "Welcome! Log in or register to manage your tasks."))

    row = HBox(3, 5, gap=3)
    btn_l = Button(0, 0, "Login", width=14, style=Style(fg="white", bg="blue"))
    btn_r = Button(0, 0, "Register", width=14, style=Style(fg="white", bg="green"))
    btn_q = Button(0, 0, "Quit", width=14, style=Style(fg="white", bg="red"))

    btn_l.on_click(lambda b: show_login())
    btn_r.on_click(lambda b: show_register())
    btn_q.on_click(lambda b: app.quit())

    row.add(btn_l).add(btn_r).add(btn_q)
    box.add(row)

    switch_screen(box, focus=btn_l, keys={Key.ESC: lambda: "quit"})


# ── Login screen ──────────────────────────────────────────────────────────────


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
    btn_ok = Button(0, 0, "Login", width=12, style=Style(fg="white", bg="blue"))
    btn_back = Button(
        0, 0, "Back", width=12, style=Style(fg="white", bg="bright_black")
    )
    row.add(btn_ok).add(btn_back)
    box.add(row)

    def do_login(b=None):
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
        show_todos()

    btn_ok.on_click(do_login)
    btn_back.on_click(lambda b: show_welcome())

    def _on_enter():
        if app.focused is inp_user:
            app.focus(inp_pass)
        elif app.focused is inp_pass:
            do_login()
        elif app.focused is not None:
            app.focused.on_key(Key.ENTER)

    switch_screen(
        box,
        focus=inp_user,
        keys={Key.ENTER: _on_enter, Key.ESC: lambda: show_welcome()},
    )


# ── Register screen ───────────────────────────────────────────────────────────


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
    btn_ok = Button(0, 0, "Register", width=14, style=Style(fg="white", bg="green"))
    btn_back = Button(
        0, 0, "Back", width=14, style=Style(fg="white", bg="bright_black")
    )
    row.add(btn_ok).add(btn_back)
    box.add(row)

    def do_register(b=None):
        u = inp_user.value.strip()
        p = inp_pass.value.strip()
        if not u or not p:
            show_register("Please fill in both fields.")
            return
        users = data.setdefault("users", {})
        if u in users:
            show_register(f"Username '{u}' is already taken.")
            return
        users[u] = {"password": p, "tasks": []}
        save_data()
        current_user[0] = u
        show_todos()

    btn_ok.on_click(do_register)
    btn_back.on_click(lambda b: show_welcome())

    def _on_enter():
        if app.focused is inp_user:
            app.focus(inp_pass)
        elif app.focused is inp_pass:
            do_register()
        elif app.focused is not None:
            app.focused.on_key(Key.ENTER)

    switch_screen(
        box,
        focus=inp_user,
        keys={Key.ENTER: _on_enter, Key.ESC: lambda: show_welcome()},
    )


# ── To-do screen ──────────────────────────────────────────────────────────────


def show_todos():
    username = current_user[0]
    tasks = data["users"][username]["tasks"]

    box = Box(
        2,
        1,
        "1500x660",
        border="rounded",
        style=Style(fg="cyan", bg="black"),
        title=f" To-Do — {username} ",
    )

    status_lbl = Label(3, 1, "", style=Style(fg="bright_black"))
    box.add(status_lbl)

    cl = CheckList(3, 3, height=8, width=44, style=Style(fg="white", bg="black"))
    box.add(cl)

    box.add(Label(3, 12, "─" * 44, style=Style(fg="cyan")))

    inp = Input(3, 14, 32, placeholder="New task…")
    box.add(inp)
    btn_add = Button(37, 14, "Add", width=9, style=Style(fg="white", bg="green"))
    box.add(btn_add)

    btn_del = Button(3, 16, "Delete", width=12, style=Style(fg="white", bg="red"))
    btn_clear = Button(
        17, 16, "Clear Done", width=14, style=Style(fg="white", bg="magenta")
    )
    btn_out = Button(
        33, 16, "Logout", width=11, style=Style(fg="white", bg="bright_black")
    )
    box.add(btn_del)
    box.add(btn_clear)
    box.add(btn_out)

    box.add(
        Label(
            3,
            18,
            "Tab navigate  •  Enter/Space toggle  •  ESC logout",
            style=Style(fg="bright_black"),
        )
    )

    selected_task = [None]

    def _update_status():
        done = sum(1 for t in tasks if t["done"])
        n = len(tasks)
        status_lbl.text = (
            "No tasks yet"
            if n == 0
            else f"{done} of {n} task{'s' if n != 1 else ''} done"
        )

    def _rebuild(keep_idx=True):
        saved = cl._index
        cl.clear()
        for task in tasks:
            cl.append(CheckItem(task["text"], task, checked=task["done"]))
        if keep_idx and tasks:
            cl._index = min(saved, len(tasks) - 1)
            cl._clamp_scroll()
        selected_task[0] = tasks[cl._index] if tasks else None
        _update_status()

    def _on_change(task):
        selected_task[0] = task

    def _on_toggle(task, checked):
        task["done"] = checked
        save_data()
        _update_status()

    def _add(b=None):
        text = inp.value.strip()
        if not text:
            return
        task = {"text": text, "done": False}
        tasks.append(task)
        cl.append(CheckItem(text, task, checked=False))
        inp.value = ""
        inp.cursor_pos = 0
        save_data()
        _update_status()
        app.focus(cl)

    def _delete(b=None):
        task = selected_task[0]
        if task is None:
            return
        idx = next((i for i, t in enumerate(tasks) if t is task), None)
        if idx is not None:
            tasks.pop(idx)
            save_data()
            _rebuild(keep_idx=True)

    def _clear_done(b=None):
        tasks[:] = [t for t in tasks if not t["done"]]
        save_data()
        _rebuild()

    def _logout(b=None):
        current_user[0] = None
        show_welcome()

    cl.on_change(_on_change)
    cl.on_toggle(_on_toggle)
    btn_add.on_click(_add)
    btn_del.on_click(_delete)
    btn_clear.on_click(_clear_done)
    btn_out.on_click(_logout)

    def _on_enter():
        if app.focused is inp:
            _add()
        elif app.focused is not None:
            app.focused.on_key(Key.ENTER)

    _rebuild()

    switch_screen(
        box, focus=cl, keys={Key.ENTER: _on_enter, Key.ESC: lambda: _logout()}
    )


# ── Start ─────────────────────────────────────────────────────────────────────

show_welcome()
app.run()
