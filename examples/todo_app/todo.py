"""To-do list — screens, per-screen keys, and widgets that keep their state.

Four screens (welcome, login, register, todos), each built **once** and refilled
on the way in rather than rebuilt on every switch. Two consequences worth
noticing while using it:

  • Type half a username, hit Back, come straight in again — it's still there.
    Nothing was thrown away, because a screen owns its widget list.

  • The login error is a hidden `Label`, not a widget added on the retry. A
    hidden widget takes no space and can't be Tabbed into, so it reads exactly
    like not being there — without rebuilding the form (and losing what was
    typed) just to show a message.

The Add and Delete buttons use `disabled` rather than click handlers that
silently do nothing, and per-screen `on_key` lets Esc mean "back" here and
"quit" there with no dispatcher in the middle checking which screen is up.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Key, Style
from cozy_tui.widgets import Box, Button, CheckItem, CheckList, HBox, Input, Label

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
current_user = [None]

# ── App & screens ─────────────────────────────────────────────────────────────

app = App(full=True, style=Style(fg="white", bg="black"))

welcome = app.screen("welcome")
login = app.screen("login")
register = app.screen("register")
todos = app.screen("todos")

MUTED = Style(fg="bright_black")
ERROR = Style(fg="red")


def show_error(label, message):
    label.text = f"✗  {message}"
    label.visible = True


def clear_error(label):
    label.visible = False


def submit_form(inp_user, inp_pass, action):
    """Enter moves username → password → submit, and otherwise goes to whatever
    has focus (so it still activates a Button)."""
    if app.focused is inp_user:
        app.focus(inp_pass)
    elif app.focused is inp_pass:
        action()
    elif app.focused is not None:
        app.focused.on_key(Key.ENTER)


def credentials_form(screen, title, color, action_label, action, hints):
    """Login and register differ only in wording and in what the action button
    does, so one builder covers both. Returns its two Inputs and error Label."""
    box = Box(
        2,
        1,
        "900x390",
        border="rounded",
        style=Style(fg=color, bg="black"),
        title=title,
    )
    inp_user = Input(13, 2, 22, placeholder=hints[0])
    inp_pass = Input(13, 4, 22, placeholder=hints[1], masked=True)
    box.add(Label(3, 2, "Username:"))
    box.add(inp_user)
    box.add(Label(3, 4, "Password:"))
    box.add(inp_pass)

    error = Label(3, 6, "", style=ERROR)
    error.visible = False  # built once, shown on demand — see the module docstring
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
    screen.on_key(Key.ESC, lambda: app.show(welcome))
    screen.on_key(Key.ENTER, lambda: submit_form(inp_user, inp_pass, action))
    screen.on_show(lambda _s: clear_error(error))
    return inp_user, inp_pass, error


# ── welcome ───────────────────────────────────────────────────────────────────

welcome_box = Box(
    2,
    1,
    "900x270",
    border="rounded",
    style=Style(fg="cyan", bg="black"),
    title=" TO-DO LIST ",
)
welcome_box.add(Label(3, 2, "Welcome! Log in or register to manage your tasks."))

_row = HBox(3, 5, gap=3)
_btn_login = Button(0, 0, "Login", width=14, style=Style(fg="white", bg="blue"))
_btn_register = Button(0, 0, "Register", width=14, style=Style(fg="white", bg="green"))
_btn_quit = Button(0, 0, "Quit", width=14, style=Style(fg="white", bg="red"))
_btn_login.on_click(lambda _b: app.show(login))
_btn_register.on_click(lambda _b: app.show(register))
_btn_quit.on_click(lambda _b: app.quit())
_row.add(_btn_login).add(_btn_register).add(_btn_quit)
welcome_box.add(_row)

welcome.add(welcome_box)
welcome.focus(_btn_login)
welcome.on_key(Key.ESC, app.quit, description="Quit", section="Actions")


# ── login ─────────────────────────────────────────────────────────────────────


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
    app.show(todos)


login_user, login_pass, login_error = credentials_form(
    login, " LOGIN ", "blue", "Login", do_login, ("your username", "your password")
)


# ── register ──────────────────────────────────────────────────────────────────


def do_register():
    user, password = reg_user.value.strip(), reg_pass.value.strip()
    if not user or not password:
        return show_error(reg_error, "Please fill in both fields.")
    users = data.setdefault("users", {})
    if user in users:
        return show_error(reg_error, f"Username '{user}' is already taken.")
    users[user] = {"password": password, "tasks": []}
    save_data()
    current_user[0] = user
    app.show(todos)


reg_user, reg_pass, reg_error = credentials_form(
    register,
    " REGISTER ",
    "green",
    "Register",
    do_register,
    ("choose a username", "choose a password"),
)


# ── todos ─────────────────────────────────────────────────────────────────────

todo_box = Box(
    2,
    1,
    "1500x660",
    border="rounded",
    style=Style(fg="cyan", bg="black"),
    title=" To-Do ",
)

status_label = Label(3, 1, "", style=MUTED)
todo_box.add(status_label)

check_list = CheckList(3, 3, height=8, width=44, style=Style(fg="white", bg="black"))
todo_box.add(check_list)
todo_box.add(Label(3, 12, "─" * 44, style=Style(fg="cyan")))

new_task = Input(3, 14, 32, placeholder="New task…")
todo_box.add(new_task)
btn_add = Button(37, 14, "Add", width=9, style=Style(fg="white", bg="green"))
todo_box.add(btn_add)

btn_delete = Button(3, 16, "Delete", width=12, style=Style(fg="white", bg="red"))
btn_clear = Button(17, 16, "Clear Done", width=14, style=Style(fg="white", bg="magenta"))
btn_logout = Button(
    33, 16, "Logout", width=11, style=Style(fg="white", bg="bright_black")
)
for _button in (btn_delete, btn_clear, btn_logout):
    todo_box.add(_button)

todo_box.add(
    Label(3, 18, "Tab navigate  •  Enter/Space toggle  •  ESC logout", style=MUTED)
)

todos.add(todo_box)
todos.focus(check_list)

selected_task = [None]


def tasks():
    return data["users"][current_user[0]]["tasks"]


def update_status():
    items = tasks()
    done = sum(1 for task in items if task["done"])
    status_label.text = (
        "No tasks yet"
        if not items
        else f"{done} of {len(items)} task{'s' if len(items) != 1 else ''} done"
    )
    # Nothing selected → nothing to delete. Greying the buttons out says so
    # before they're pressed, which a no-op click handler never could.
    btn_delete.disabled = selected_task[0] is None
    btn_clear.disabled = not any(task["done"] for task in items)


def sync_add_button(_text=None):
    btn_add.disabled = not new_task.value.strip()


def rebuild(keep_position=True):
    """Refill the list from the current user's tasks. `selected_index` is a
    public property with a setter, so restoring the cursor after a delete
    doesn't mean reaching into the widget's internals."""
    saved = check_list.selected_index or 0
    check_list.clear()
    for task in tasks():
        check_list.append(CheckItem(task["text"], task, checked=task["done"]))
    if keep_position and tasks():
        check_list.selected_index = saved
    selected_task[0] = check_list.selected
    update_status()


def on_select(task):
    selected_task[0] = task
    update_status()


def on_toggle(task, checked):
    task["done"] = checked
    save_data()
    update_status()


def add_task(_b=None):
    text = new_task.value.strip()
    if not text:
        return
    task = {"text": text, "done": False}
    tasks().append(task)
    check_list.append(CheckItem(text, task, checked=False))
    new_task.value = ""
    new_task.cursor_pos = 0
    sync_add_button()
    save_data()
    selected_task[0] = check_list.selected
    update_status()
    app.focus(check_list)


def delete_task(_b=None):
    task = selected_task[0]
    if task is None:
        return
    items = tasks()
    index = next((i for i, t in enumerate(items) if t is task), None)
    if index is not None:
        items.pop(index)
        save_data()
        rebuild()


def clear_done(_b=None):
    items = tasks()
    items[:] = [task for task in items if not task["done"]]
    save_data()
    rebuild(keep_position=False)


def logout(_b=None):
    current_user[0] = None
    app.show(welcome)


check_list.on_change(on_select)
check_list.on_toggle(on_toggle)
new_task.on_change(sync_add_button)
btn_add.on_click(add_task)
btn_delete.on_click(delete_task)
btn_clear.on_click(clear_done)
btn_logout.on_click(logout)


def enter_on_todos():
    if app.focused is new_task:
        add_task()
    elif app.focused is not None:
        app.focused.on_key(Key.ENTER)


def load_user(_screen=None):
    """on_show: point the screen at whoever just logged in. The widgets are the
    same ones every time; only their contents change."""
    todo_box.title = f" To-Do — {current_user[0]} "
    new_task.value = ""
    sync_add_button()
    rebuild(keep_position=False)


todos.on_show(load_user)
todos.on_key(Key.ENTER, enter_on_todos)
todos.on_key(Key.ESC, logout, description="Log out", section="Actions")


# ── Start ─────────────────────────────────────────────────────────────────────

app.show(welcome)
app.run()
