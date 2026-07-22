"""The Cheat Console (backtick key) -- a dev/testing tool for setting up a
specific scenario in seconds ("does the shark actually eat fish?") instead
of grinding money and raising fish for real every time. Not eval()/exec():
parse_command() uses ast.parse(mode="eval") structurally and
ast.literal_eval() per-argument, so a typed command can only ever supply
plain literal values (strings/numbers/bools/None) -- never call anything,
access an attribute, or run arbitrary code."""

import ast
import textwrap
from collections import namedtuple

from cozy_tui.events import Key
from cozy_tui.style import Style
from cozy_tui.widget import Widget
from cozy_tui.widgets.selection._search_palette import draw_panel_frame

from .constants import (
    CONSOLE_LOG_LIMIT,
    DECORATION_SHOP_ITEMS,
    FOOD_PACK_PRICE,
    FOOD_PACK_SIZE,
    SHOP_ITEMS,
    TREAT_SHOP_ITEMS,
)


class ConsoleError(Exception):
    """A user-facing console error -- the message is shown as-is in the
    console's log, never a raw Python traceback."""


def parse_command(text: str):
    """ "name(arg1, kw=val, ...)" or a bare "name" -> (name, positional_args,
    kwargs). Structural parse only (ast.parse(mode="eval")) plus
    ast.literal_eval() per-argument -- this never executes anything, unlike
    eval(). Raises ConsoleError on anything that doesn't parse as that
    shape, or whose arguments aren't plain literals."""
    text = text.strip()
    if not text:
        raise ConsoleError("Type a command, or `help` to see what's available.")
    if "(" not in text:
        return text, [], {}
    try:
        node = ast.parse(text, mode="eval").body
    except SyntaxError:
        raise ConsoleError(f"Couldn't parse: {text!r}")
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        raise ConsoleError("Expected a command like name(arg=value).")
    positional = []
    for arg in node.args:
        try:
            positional.append(ast.literal_eval(arg))
        except (ValueError, SyntaxError):
            raise ConsoleError(
                "Arguments must be plain values (a string or a number), "
                "not expressions."
            )
    kwargs = {}
    for kw in node.keywords:
        if kw.arg is None:  # a **spread -- not a plain literal
            raise ConsoleError(
                "Arguments must be plain values (a string or a number), "
                "not expressions."
            )
        try:
            kwargs[kw.arg] = ast.literal_eval(kw.value)
        except (ValueError, SyntaxError):
            raise ConsoleError(
                f"Argument {kw.arg!r} must be a plain value (a string or a number)."
            )
    return node.func.id, positional, kwargs


Command = namedtuple("Command", "usage handler")


def build_console_commands(
    *,
    state,
    fish,
    add_fish,
    spawn_fish,
    buy_food,
    buy_treat,
    add_decoration,
    refresh_stats,
    set_day_phase,
    spawn_food,
    give_nightmare,
    give_dream,
) -> dict:
    """The command registry, closing over the same real state/mutators the
    Shop/Inspector already use (see aquarium.py's main()) -- every command
    is a real effect on the live tank, not a separate cheat-only code path."""

    def _find_species(name):
        species = next(
            (s for s in SHOP_ITEMS if s.name.lower() == str(name).lower()), None
        )
        if species is None:
            names = ", ".join(s.name for s in SHOP_ITEMS)
            raise ConsoleError(f"Unknown species: {name!r}. Try one of: {names}.")
        return species

    def _find_fish(name):
        target = next((f for f in fish if f.display_name == name), None)
        if target is None:
            raise ConsoleError(f"No fish named {name!r} in the tank.")
        return target

    def _require_number(value, what: str) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ConsoleError(f"{what} must be a number.")
        return float(value)

    def cmd_spawn_fish(args, kwargs):
        species_name = kwargs.get("species", args[0] if args else None)
        if species_name is None:
            raise ConsoleError(
                'Usage: spawn_fish(species="Goldfish", name=None, amount=1)'
            )
        species = _find_species(species_name)
        name = kwargs.get("name")
        amount = kwargs.get("amount", 1)
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 1:
            raise ConsoleError("amount must be a positive whole number.")
        amount = min(amount, 20)  # a fat-fingered amount=99999 stays harmless
        spawned = [add_fish(species) for _ in range(amount)]
        if name:
            for f in spawned:
                f.display_name = str(name)
        return f"Spawned {len(spawned)} {species.name}(s)."

    def _set_fish_stat(attr: str, args, kwargs):
        fish_name = kwargs.get("fish_name", args[0] if args else None)
        amount = kwargs.get("amount", args[1] if len(args) > 1 else None)
        if fish_name is None or amount is None:
            raise ConsoleError(f"Usage: set_{attr}(fish_name=..., amount=...)")
        target = _find_fish(str(fish_name))
        clamped = max(0.0, min(100.0, _require_number(amount, "amount")))
        setattr(target, attr, clamped)
        return f"Set {target.display_name}'s {attr} to {clamped:.0f}."

    def cmd_set_health(args, kwargs):
        return _set_fish_stat("health", args, kwargs)

    def cmd_set_hunger(args, kwargs):
        return _set_fish_stat("hunger", args, kwargs)

    def _set_economy(key: str, args, kwargs):
        amount = kwargs.get("amount", args[0] if args else None)
        if amount is None:
            raise ConsoleError(f"Usage: set_{key}(amount=...)")
        state[key] = max(0, int(_require_number(amount, "amount")))
        refresh_stats()
        return f"Set {key} to {state[key]}."

    def cmd_set_money(args, kwargs):
        return _set_economy("money", args, kwargs)

    def cmd_set_food(args, kwargs):
        return _set_economy("food", args, kwargs)

    def _purchase(price: int, callback, message: str) -> str:
        if state["money"] < price:
            raise ConsoleError("Not enough money!")
        state["money"] -= price
        callback()
        refresh_stats()
        return message

    def cmd_buy(args, kwargs):
        item_name = kwargs.get("name", args[0] if args else None)
        if item_name is None:
            raise ConsoleError('Usage: buy(name="Shark")')
        item_name = str(item_name)
        species = next(
            (s for s in SHOP_ITEMS if s.name.lower() == item_name.lower()), None
        )
        if species is not None:
            return _purchase(
                species.price, lambda: spawn_fish(species), f"Bought a {species.name}."
            )
        decoration = next(
            (d for d in DECORATION_SHOP_ITEMS if d.kind.lower() == item_name.lower()),
            None,
        )
        if decoration is not None:
            return _purchase(
                decoration.price,
                lambda: add_decoration(decoration),
                f"Bought a {decoration.kind}.",
            )
        treat = next(
            (t for t in TREAT_SHOP_ITEMS if t.kind.lower() == item_name.lower()), None
        )
        if treat is not None:
            return _purchase(
                treat.price, lambda: buy_treat(treat), f"Bought {treat.kind}."
            )
        if item_name.lower() in ("food", "fish food"):
            return _purchase(
                FOOD_PACK_PRICE, buy_food, f"Bought {FOOD_PACK_SIZE} fish food."
            )
        raise ConsoleError(f"Unknown item: {item_name!r}.")

    def cmd_set_time(args, kwargs):
        phase = kwargs.get("phase", args[0] if args else None)
        if phase is None:
            raise ConsoleError('Usage: set_time("day" | "morning" | "night")')
        try:
            label = set_day_phase(str(phase))
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"Set the time to {label}."

    def cmd_spawn(args, kwargs):
        kind = kwargs.get("item", args[0] if args else None)
        if kind is None:
            raise ConsoleError('Usage: spawn(item="Pizza", amount=1)')
        amount = kwargs.get("amount", args[1] if len(args) > 1 else 1)
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 1:
            raise ConsoleError("amount must be a positive whole number.")
        amount = min(amount, 50)  # a fat-fingered amount=99999 stays harmless
        try:
            count, label = spawn_food(str(kind), amount)
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"Dropped {count} {label} into the tank."

    def cmd_give_nightmare(args, kwargs):
        name = kwargs.get("fish_name", args[0] if args else None)
        if name is None:
            raise ConsoleError('Usage: give_nightmare(fish_name="Steve")')
        target = _find_fish(str(name))
        give_nightmare(target)
        return f"Gave {target.display_name} a nightmare."

    def cmd_give_dream(args, kwargs):
        name = kwargs.get("fish_name", args[0] if args else None)
        if name is None:
            raise ConsoleError('Usage: give_dream(fish_name="Alex", category="happy")')
        category = kwargs.get("category", args[1] if len(args) > 1 else None)
        target = _find_fish(str(name))
        try:
            title = give_dream(target, str(category) if category is not None else None)
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"Gave {target.display_name} a dream about {title}."

    def cmd_help(_args, _kwargs):
        return "\n".join(f"{name}: {cmd.usage}" for name, cmd in commands.items())

    commands = {
        "help": Command("list every available command", cmd_help),
        "spawn_fish": Command(
            "spawn_fish(species: name of the species, name: the fish's name "
            "(optional), amount: how many to spawn (optional), default is 1)",
            cmd_spawn_fish,
        ),
        "set_health": Command(
            "set_health(fish_name: the fish to apply this to, amount: the "
            "health it should have, 0-100)",
            cmd_set_health,
        ),
        "set_hunger": Command(
            "set_hunger(fish_name: the fish to apply this to, amount: the "
            "hunger it should have, 0-100)",
            cmd_set_hunger,
        ),
        "set_money": Command(
            "set_money(amount: the amount of money to have)", cmd_set_money
        ),
        "set_food": Command(
            "set_food(amount: the amount of food to have)", cmd_set_food
        ),
        "buy": Command(
            "buy(name: the name of the fish/decoration/treat/food to buy) "
            "-- still costs money, just like the real Shop",
            cmd_buy,
        ),
        "set_time": Command(
            'set_time(phase: "day", "morning", or "night") -- jumps the '
            "day/night clock to that time of day",
            cmd_set_time,
        ),
        "spawn": Command(
            'spawn(item: a special food like "Pizza", amount: how many '
            "(optional, default 1)) -- drops it in the tank at your mouse for "
            "fish to eat, free (unlike the Shop)",
            cmd_spawn,
        ),
        "give_nightmare": Command(
            "give_nightmare(fish_name: the fish to spook) -- a forced bad "
            "dream and the wake-up scare that follows",
            cmd_give_nightmare,
        ),
        "give_dream": Command(
            "give_dream(fish_name: the fish, category: happy/food/friendship/"
            "home/fantasy (optional)) -- gives it a nice dream to view",
            cmd_give_dream,
        ),
    }
    return commands


def run_console_command(commands: dict, text: str) -> str:
    """Parse and dispatch one typed line against `commands`
    (build_console_commands()'s registry) -- the single entry point
    CheatConsole.on_run is wired to."""
    name, args, kwargs = parse_command(text)
    command = commands.get(name)
    if command is None:
        raise ConsoleError(
            f"Unknown command: {name!r}. Type help to see what's available."
        )
    return command.handler(args, kwargs)


_VISIBLE_LINES = 14
_WIDTH = 64
_WELCOME = (
    "=== Welcome to the TermQuarium Cheat Console ===",
    "Type help to see the available commands.",
    "",
    "Getting started:",
    '  spawn_fish(species="Goldfish")',
)


class CheatConsole(Widget):
    """A self-contained modal console (own text buffer, own scrollback, own
    draw()), the same "no child Input/ListView" shape as PromptDialog/
    ConfirmDialog -- a modal routes every key straight to this one widget,
    so splitting the typing half and the scrollback half into two child
    widgets would need a hand-written wrapper deciding which key goes where
    anyway, for no less code. `on_run(text) -> str` (raising ConsoleError
    for a user-facing problem) is the only thing the caller needs to
    supply -- see aquarium.py's _open_console()."""

    focusable = True

    def __init__(self, on_run, *, width: int = _WIDTH, style=None):
        super().__init__(0, 0, style or Style(fg="white", bg="black"))
        self.on_run = on_run
        self.width = max(20, width)
        self.buffer = ""
        self.lines: list[tuple[str, bool]] = []  # (text, is_error)
        self._history: list[str] = []
        self._history_index = None

    def natural_width(self, scale) -> int:
        return self.width + 2

    def natural_height(self, scale) -> int:
        return _VISIBLE_LINES + 5  # border(2) + title + input + hint

    def contains(self, col: int, row: int) -> bool:
        return self.abs_x <= col < self.abs_x + self.natural_width(
            1
        ) and self.abs_y <= row < self.abs_y + self.natural_height(1)

    def _emit(self, text: str, is_error: bool) -> None:
        # Word-wrap into the panel's own interior width -- without this, a
        # long line (help()'s usage strings, an "> {typed command}" echo)
        # either got silently truncated (ljust(w)[:w] in draw()) or, worse,
        # multiple newline-joined lines (help()'s own "\n".join(...)) landed
        # in *one* `lines` entry and rendered as one run-together row.
        wrap_width = max(1, self.width - 2)
        for raw_line in text.split("\n"):
            for wrapped in textwrap.wrap(raw_line, width=wrap_width) or [""]:
                self.lines.append((wrapped, is_error))

    def _run(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        self._emit(f"> {text}", False)
        self._history.append(text)
        del self._history[:-CONSOLE_LOG_LIMIT]
        self._history_index = None
        try:
            result = self.on_run(text)
            if result:
                self._emit(result, False)
        except ConsoleError as error:
            self._emit(str(error), True)
        del self.lines[:-CONSOLE_LOG_LIMIT]

    def on_key(self, key) -> None:
        if key == Key.ENTER:
            self._run(self.buffer)
            self.buffer = ""
        elif key == Key.BACKSPACE:
            self.buffer = self.buffer[:-1]
        elif key == Key.UP:
            if self._history:
                self._history_index = (
                    len(self._history) - 1
                    if self._history_index is None
                    else max(0, self._history_index - 1)
                )
                self.buffer = self._history[self._history_index]
        elif key == Key.DOWN:
            if self._history_index is not None:
                self._history_index += 1
                if self._history_index >= len(self._history):
                    self._history_index = None
                    self.buffer = ""
                else:
                    self.buffer = self._history[self._history_index]
        elif isinstance(key, str) and len(key) == 1 and key.isprintable():
            self.buffer += key

    def _palette(self):
        from cozy_tui.theme import get_theme  # local: theme.py builds on Style

        raw_bg = self.style.raw_bg
        border = Style(fg=get_theme().accent, bg=raw_bg, styles=["bold"])
        error = Style(fg="bright_red", bg=raw_bg)
        dim = Style(fg="bright_black", bg=raw_bg)
        return self.style, border, error, dim

    def draw(self, canvas) -> None:
        panel, border, error_style, dim = self._palette()
        x, y, w = self.abs_x, self.abs_y, self.width
        h = self.natural_height(1)
        draw_panel_frame(canvas, x, y, w, h, border, panel)
        canvas.write(x + 1, y + 1, " Cheat Console".ljust(w)[:w], border)

        body = self.lines if self.lines else [(line, False) for line in _WELCOME]
        for row, (text, is_error) in enumerate(body[-_VISIBLE_LINES:]):
            style = error_style if is_error else panel
            canvas.write(x + 1, y + 2 + row, (" " + text).ljust(w)[:w], style)

        input_row = y + 2 + _VISIBLE_LINES
        line = "> " + self.buffer
        line = line[-(w - 2) :] if len(line) > w - 2 else line
        canvas.write(x + 1, input_row, (" " + line + "▏").ljust(w)[:w], panel)
        canvas.write(
            x + 1,
            input_row + 1,
            "  Enter: run    Esc: close    Up/Down: history".ljust(w)[:w],
            dim,
        )
