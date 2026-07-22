"""Deploy console — State, Log, and overlays in one app.

This merges three older single-feature demos into one thing that has a reason
to use all three, because that's how they actually show up together:

  • **State** is the app's data. `service`, `stage`, and `percent` are the
    entire model; nothing below ever updates a widget by hand. `service` alone
    drives the panel's border title, the header label, and the log prefix — add
    a fourth reader and it's one more line, not an edit to every function that
    renames a service.

  • **Log** is the deploy output. It owns its rows and its history cap; the app
    just appends strings. `markup=True` colors the level tag inside each line
    while the message beside it stays plain, which is what makes a fast stream
    scannable.

  • **Overlays** guard the irreversible bits. Deploying opens a hand-built
    modal `Box` (raw `open_overlay`, so you can see what the ready-made dialogs
    are made of); rolling back uses `app.confirm()`; renaming uses
    `app.prompt()` and writes back into `service` explicitly — binding is
    one-way on purpose, so an Input and a State never fight over who owns the
    value.

The seam worth watching: `deploy()` doesn't know a dialog exists, `confirm_deploy()`
doesn't know what deploying does, and no widget knows about any other. The
States are the only thing in the middle.

Run it:

    python examples/deploy/deploy.py

Keys: D deploy · R rollback · N rename · C clear log · Esc quit
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Key, State, Style
from cozy_tui.markup import escape
from cozy_tui.widgets import Box, Button, HBox, Label, Log, ProgressBar

app = App(full=True, title="Deploy")

MAX_LINES = 500

LEVELS = {"DEBUG": "dim", "INFO": "cyan", "WARN": "bold yellow", "ERROR": "bold red"}

# The deploy itself: (percent_at_completion, level, message). Deterministic
# rather than random -- a demo you can read along with beats one that surprises
# you, and it makes the whole thing testable without seeding anything.
STEPS = [
    (8, "INFO", "resolving manifest for tag v2.4.1"),
    (18, "DEBUG", "cache hit: layers 1-6 of 9"),
    (30, "INFO", "building image"),
    (42, "DEBUG", "GET /v2/registry/blobs?digest=[a-f0-9]+"),  # not markup
    (55, "INFO", "pushing image (142 MB)"),
    (64, "WARN", "slow layer upload — 41s for 38 MB"),
    (75, "INFO", "draining connections from 3 old pods"),
    (88, "INFO", "health check passed on 3 of 3 pods"),
    (100, "INFO", "traffic shifted — deploy complete"),
]


# ── the entire application state ─────────────────────────────────────────────
# Explicit by design: these are reactive because they're wrapped in State().
# A plain `service = "checkout-api"` would stay a plain string forever.

service = State("checkout-api")
stage = State("Idle — press Deploy")
percent = State(0)


# ── layout ───────────────────────────────────────────────────────────────────
# Every `service` / `stage` / `percent` below is a State handed to a widget
# where a plain value would normally go. That is the whole integration.

panel = Box(0, 0, "600x110", title=service, border="rounded")
panel.add(Label(2, 1, service, style=Style(fg="bright_cyan", styles=["bold"])))
panel.add(Label(2, 3, stage, style=Style(fg="bright_black")))
panel.add(ProgressBar(2, 5, progress=percent, width=44, style=Style(fg="green")))

buttons = HBox(2, 7, gap=2)
log = Log(markup=True, max_lines=MAX_LINES)
footer = Label(0, 0, "", markup=True, style=Style(fg="bright_black"))

app.dock(panel, "top", margin=1)
app.dock(footer, "bottom", margin=1)
app.dock(log, "fill", margin=1)


# ── logging ──────────────────────────────────────────────────────────────────


def emit(level: str, text: str) -> None:
    """One line into the Log, level tag colored, message left plain.

    `service.value` is read here rather than bound, because a log line is a
    snapshot: renaming the service later must not rewrite history. That's the
    difference between a State *reader* and a State *binding*, and it's worth
    being deliberate about which one a given piece of UI wants.
    """
    log.log(f"[{LEVELS[level]}]{level:<5}[/] [dim]{service.value}[/] {text}")


def update_footer(*_args) -> None:
    footer.text = (
        f"[bright_white]{len(log.lines)}[/] lines (cap {MAX_LINES})  ·  "
        "[dim]D deploy · R rollback · N rename · C clear · Esc quit[/]"
    )


# Any change to the stage is worth re-rendering the footer's counter, and
# subscribing beats calling update_footer() from six different places.
stage.subscribe(update_footer)


# ── behaviour ────────────────────────────────────────────────────────────────

timer = None
step_index = 0


def tick() -> None:
    """Advance the deploy one step. Runs on the main thread from app.every(),
    so these State assignments repaint on the loop's very next frame."""
    global step_index
    target, level, message = STEPS[step_index]
    percent.value = target
    emit(level, message)
    step_index += 1
    update_footer()

    if step_index >= len(STEPS):
        finish()


def finish() -> None:
    global timer
    if timer is not None:
        app.cancel(timer)
        timer = None
    stage.value = "Live ✔"
    app.toast(f"{service.value} is live", level="success")


def deploy() -> None:
    """Start a deploy. Knows nothing about the dialog that gated it."""
    global timer, step_index
    if timer is not None:
        return
    step_index = 0
    percent.value = 0
    stage.value = "Deploying…"
    emit("INFO", f"deploy started by {escape(current_user())}")
    timer = app.every(0.45, tick)


def rollback() -> None:
    global timer
    if timer is not None:
        app.cancel(timer)
        timer = None
    percent.value = 0
    stage.value = "Rolled back"
    emit("WARN", "rolled back to the previous release")


def current_user() -> str:
    """Stands in for something you don't control. Run through escape() at the
    call site above: if a username genuinely contained "[red]", markup would
    otherwise obey it instead of showing it."""
    return "ops@[red]example.com"


# ── overlays ─────────────────────────────────────────────────────────────────


def confirm_deploy() -> None:
    """A modal built by hand, rather than app.confirm() — this is what the
    ready-made dialogs are underneath: an ordinary Box pushed onto the overlay
    stack with modal=True. While it's open Tab is confined to it, the
    background dims, and Esc or a click outside dismisses it."""
    dialog = Box(0, 0, "560x150", title="Confirm deploy", border="rounded")
    dialog.add(Label(2, 1, f"Deploy {service.value} to production?"))
    dialog.add(Label(2, 2, "This shifts live traffic.", style=Style(fg="bright_black")))

    def choose(go: bool):
        app.close_overlay(dialog)
        if go:
            deploy()

    row = HBox(2, 4, gap=2)
    row.add(Button(0, 0, "Cancel", width=10).on_click(lambda _b: choose(False)))
    row.add(
        Button(0, 0, "Deploy", width=10, style=Style(fg="white", bg="green")).on_click(
            lambda _b: choose(True)
        )
    )
    dialog.add(row)
    app.open_overlay(dialog, close_on_click_outside=True)


def confirm_rollback() -> None:
    """The same guard, using the built-in dialog. Note that cancelling counts
    as "no" — which is what you want for anything behind a confirmation."""
    app.confirm(
        f"Roll {service.value} back to the previous release?",
        on_yes=rollback,
        yes_label="Roll back",
    )


def rename() -> None:
    """Binding is one-way (State → widget), so writing *back* stays explicit.
    One assignment; the panel title, the header label, and every future log
    line all follow."""
    app.prompt(
        "Rename service",
        service.value,
        on_submit=lambda text: service.set(text.strip() or "checkout-api"),
    )


def clear_log() -> None:
    log.clear()
    update_footer()


buttons.add(Button(0, 0, "Deploy", width=10).on_click(lambda _b: confirm_deploy()))
buttons.add(Button(0, 0, "Rollback", width=12).on_click(lambda _b: confirm_rollback()))
buttons.add(Button(0, 0, "Rename", width=10).on_click(lambda _b: rename()))
panel.add(buttons)

app.on_key("d", confirm_deploy, description="Deploy", section="Release")
app.on_key("r", confirm_rollback, description="Rollback", section="Release")
app.on_key("n", rename, description="Rename service", section="Release")
app.on_key("c", clear_log, description="Clear log", section="Log")
app.on_key(Key.ESC, app.quit, description="Quit", section="Actions")

app.focus(buttons.children[0])
emit("INFO", "console attached")
update_footer()
app.run()
