from cozy_tui import App, Box, Label, ProgressBar, Style
from cozy_tui.events import Key

app = App(full=True, size=None, style=Style(fg="white", bg="black"))

box = Box(
    2,
    1,
    "960x630",
    border="rounded",
    style=Style(fg="cyan", bg="black"),
    title=" ProgressBar Demo ",
)

lbl_value = Label(3, 2, "Value: 0", style=Style(fg="bright_green"))
box.add(lbl_value)

# ── default width ─────────────────────────────────────────────────────────────

box.add(
    Label(3, 4, "Default (width=20, 0–100)", style=Style(fg="cyan", styles=["bold"]))
)
pb = ProgressBar(3, 5, progress=0, width=20, style=Style(fg="white", bg="black"))
box.add(pb)

# ── wide bar ──────────────────────────────────────────────────────────────────

box.add(Label(3, 7, "Wide (width=40, 0–100)", style=Style(fg="cyan", styles=["bold"])))
pb_wide = ProgressBar(3, 8, progress=0, width=40, style=Style(fg="white", bg="black"))
box.add(pb_wide)

# ── custom range ──────────────────────────────────────────────────────────────

box.add(
    Label(
        3, 10, "Custom range (width=30, 0–200)", style=Style(fg="cyan", styles=["bold"])
    )
)
pb_custom = ProgressBar(
    3, 11, progress=0, width=30, min=0, max=200, style=Style(fg="white", bg="black")
)
box.add(pb_custom)

# ── key handlers ──────────────────────────────────────────────────────────────


def update_label():
    lbl_value.text = (
        f"Value: {pb.get()}  |  wide: {pb_wide.get()}  |  custom: {pb_custom.get()}"
    )


def inc():
    pb.increment(5)
    pb_wide.increment(5)
    pb_custom.increment(10)
    update_label()


def dec():
    pb.decrement(5)
    pb_wide.decrement(5)
    pb_custom.decrement(10)
    update_label()


def reset():
    pb.set(0)
    pb_wide.set(0)
    pb_custom.set(0)
    update_label()


def full():
    pb.set(100)
    pb_wide.set(100)
    pb_custom.set(200)
    update_label()


box.add(
    Label(
        3,
        13,
        "↑/+ increment 5   ↓/- decrement 5   r reset   f fill   q quit",
        style=Style(fg="bright_black"),
    )
)

app.widgets = [box]
app._key_handlers = {
    Key.UP: inc,
    Key.DOWN: dec,
    "+": inc,
    "-": dec,
    "r": reset,
    "R": reset,
    "f": full,
    "F": full,
    "q": lambda: "quit",
}
app.run()
