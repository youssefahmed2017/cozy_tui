"""2048 — the classic slide-and-merge puzzle, in the terminal.

Arrow keys or WASD (or hjkl) slide every tile; equal tiles that collide merge
into their sum. A new 2 (or occasionally 4) appears after each move. Reach 2048
to win — then keep going for a high score. You lose when the board fills with no
moves left.

Shows off:
  * a fully custom drawing Widget painting a colored tile grid cell-by-cell,
  * truecolor tile styling (Style(bg="rgb(...)")) that auto-downgrades on
    16/256-color terminals,
  * pure, testable game logic split from rendering,
  * mouse-swipe input (drag on the board) alongside the keyboard,
  * a modal overlay (no light-dismiss) for the win / game-over screens.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Style
from cozy_tui.events import Key
from cozy_tui.widget import Widget
from cozy_tui.widgets import Box, Button, Label

SIZE = 4

# ── pure game logic (no rendering; unit-tested in tests/test_game_2048.py) ──────


def new_grid():
    return [[0] * SIZE for _ in range(SIZE)]


def _slide_row(row):
    """Slide/merge one row toward the left. Returns (new_row, points_gained)."""
    nums = [v for v in row if v]
    out, gained, i = [], 0, 0
    while i < len(nums):
        if i + 1 < len(nums) and nums[i] == nums[i + 1]:
            merged = nums[i] * 2
            out.append(merged)
            gained += merged
            i += 2  # a tile can only merge once per move
        else:
            out.append(nums[i])
            i += 1
    out += [0] * (SIZE - len(out))
    return out, gained


def move(grid, direction):
    """Apply a move ('left'/'right'/'up'/'down').

    Returns (new_grid, points_gained, moved) where ``moved`` is False when the
    move changes nothing (so no new tile should be spawned).
    """
    if direction == "left":
        rows = [row[:] for row in grid]
    elif direction == "right":
        rows = [row[::-1] for row in grid]
    elif direction == "up":
        rows = [list(col) for col in zip(*grid)]
    elif direction == "down":
        rows = [list(col)[::-1] for col in zip(*grid)]
    else:
        raise ValueError(f"unknown direction {direction!r}")

    slid, gained = [], 0
    for row in rows:
        nr, g = _slide_row(row)
        slid.append(nr)
        gained += g

    if direction == "left":
        new = slid
    elif direction == "right":
        new = [r[::-1] for r in slid]
    elif direction == "up":
        new = [list(r) for r in zip(*slid)]
    else:  # down
        new = [list(r) for r in zip(*[r[::-1] for r in slid])]

    return new, gained, new != grid


def spawn(grid, rng):
    """Place a 2 (90%) or 4 (10%) on a random empty cell. Returns its (r, c)."""
    empties = [(r, c) for r in range(SIZE) for c in range(SIZE) if grid[r][c] == 0]
    if not empties:
        return None
    r, c = rng.choice(empties)
    grid[r][c] = 4 if rng.random() < 0.1 else 2
    return r, c


def has_moves(grid):
    """True while any slide is still possible (empty cell or adjacent equal pair)."""
    for r in range(SIZE):
        for c in range(SIZE):
            v = grid[r][c]
            if v == 0:
                return True
            if c + 1 < SIZE and grid[r][c + 1] == v:
                return True
            if r + 1 < SIZE and grid[r + 1][c] == v:
                return True
    return False


def max_tile(grid):
    return max(max(row) for row in grid)


# ── styling ─────────────────────────────────────────────────────────────────────

BG = "rgb(28,26,24)"  # screen background (shows through the gaps between tiles)
EMPTY = "rgb(58,54,48)"
GOLD = "rgb(237,194,46)"

# value -> (background, foreground)
TILES = {
    2: ("rgb(238,228,218)", "rgb(90,80,70)"),
    4: ("rgb(237,224,200)", "rgb(90,80,70)"),
    8: ("rgb(242,177,121)", "rgb(255,255,255)"),
    16: ("rgb(245,149,99)", "rgb(255,255,255)"),
    32: ("rgb(246,124,95)", "rgb(255,255,255)"),
    64: ("rgb(246,94,59)", "rgb(255,255,255)"),
    128: ("rgb(237,207,114)", "rgb(255,255,255)"),
    256: ("rgb(237,204,97)", "rgb(255,255,255)"),
    512: ("rgb(237,200,80)", "rgb(255,255,255)"),
    1024: ("rgb(237,197,63)", "rgb(255,255,255)"),
    2048: (GOLD, "rgb(255,255,255)"),
}
SUPER = ("rgb(60,58,50)", "rgb(255,255,255)")  # 4096 and beyond

MUTED = Style(fg="bright_black")

TW, TH, GAP = 8, 3, 1  # tile width, tile height, gap between tiles (cells)
BW = SIZE * TW + (SIZE - 1) * GAP
BH = SIZE * TH + (SIZE - 1) * GAP


# ── the game widget ─────────────────────────────────────────────────────────────


class Game2048(Widget):
    focusable = True

    _KEYS = {
        Key.LEFT: "left", Key.RIGHT: "right", Key.UP: "up", Key.DOWN: "down",
        "a": "left", "d": "right", "w": "up", "s": "down",
        "h": "left", "l": "right", "k": "up", "j": "down",
    }

    def __init__(self, app):
        super().__init__(0, 0)
        self.app = app
        self.rng = random.Random()
        self.best = 0
        self._rect = (0, 0, 0, 0)  # board bounds in cells, for mouse hit-testing
        self._press = None
        self._over_box = None
        self.reset()

    def reset(self):
        self.grid = new_grid()
        self.score = 0
        self.state = "playing"
        self.keep_going = False
        spawn(self.grid, self.rng)
        spawn(self.grid, self.rng)
        if self._over_box is not None:
            self.app.close_overlay(self._over_box)
            self._over_box = None

    # ── input ───────────────────────────────────────────────────────────────────

    def on_key(self, key):
        if self.state != "playing":
            return
        direction = self._KEYS.get(key)
        if direction:
            self._do_move(direction)

    def _do_move(self, direction):
        new, gained, moved = move(self.grid, direction)
        if not moved:
            return
        self.grid = new
        self.score += gained
        self.best = max(self.best, self.score)
        spawn(self.grid, self.rng)

        if not self.keep_going and max_tile(self.grid) >= 2048:
            self.state = "won"
            self._show_end("You win! 🎉", f"You reached 2048 — score {self.score}", win=True)
        elif not has_moves(self.grid):
            self.state = "over"
            self._show_end("Game Over", f"No moves left — score {self.score}", win=False)

    def _continue(self):
        self.keep_going = True
        self.state = "playing"
        if self._over_box is not None:
            self.app.close_overlay(self._over_box)
            self._over_box = None

    def _show_end(self, title, message, win):
        box = Box(0, 0, "440x120", title=title, border="bold",
                  style=Style(fg="white", bg="black"))
        box.add(Label(2, 1, message))
        x = 2
        if win:
            box.add(Button(x, 3, "Keep going").on_click(lambda b: self._continue()))
            x += 13
        box.add(Button(x, 3, "New game").on_click(lambda b: self.reset()))
        box.add(Button(x + 11, 3, "Quit").on_click(lambda b: self.app.quit()))
        self._over_box = box
        self.app.open_overlay(box, close_on_escape=False, close_on_click_outside=False)

    # mouse: a drag across the board slides in the drag's dominant direction.
    def contains(self, col, row):
        x, y, w, h = self._rect
        return x <= col < x + w and y <= row < y + h

    def on_mouse_click(self, col=None, row=None):
        self._press = (col, row)

    def on_mouse_release(self, col=None, row=None):
        if self._press is None or self.state != "playing":
            self._press = None
            return
        px, py = self._press
        self._press = None
        dx, dy = (col - px), (row - py)
        # Cells are ~twice as tall as wide, so weight horizontal distance down.
        if abs(dx) * 0.5 >= abs(dy):
            if abs(dx) >= 2:
                self._do_move("right" if dx > 0 else "left")
        elif abs(dy) >= 1:
            self._do_move("down" if dy > 0 else "up")

    # ── drawing ───────────────────────────────────────────────────────────────

    def natural_width(self, scale):
        return BW

    def natural_height(self, scale):
        return BH

    def _tile_style(self, value):
        bg, fg = TILES.get(value, SUPER)
        return Style(bg=bg), Style(fg=fg, bg=bg, styles=["bold"])

    def draw(self, canvas):
        cols, rows = canvas.cols, canvas.rows
        block_h = BH + 6  # title + score + board + footer, with blank spacers
        top = max(0, (rows - block_h) // 2)
        ox = max(0, (cols - BW) // 2)
        oy = top + 4
        self._rect = (ox, oy, BW, BH)

        # title + score
        title = "2 0 4 8"
        canvas.write(ox + (BW - len(title)) // 2, top, title,
                     Style(fg=GOLD, styles=["bold"]))
        score = f"Score {self.score}     Best {self.best}"
        canvas.write(ox + (BW - len(score)) // 2, top + 2, score,
                     Style(fg="bright_white", styles=["bold"]))

        # tiles
        for r in range(SIZE):
            for c in range(SIZE):
                value = self.grid[r][c]
                x = ox + c * (TW + GAP)
                y = oy + r * (TH + GAP)
                if value == 0:
                    fill = Style(bg=EMPTY)
                    for i in range(TH):
                        canvas.write(x, y + i, " " * TW, fill)
                    continue
                block, text = self._tile_style(value)
                for i in range(TH):
                    canvas.write(x, y + i, " " * TW, block)
                canvas.write(x, y + TH // 2, str(value).center(TW), text)

        # footer
        hint = "←↑↓→ / WASD slide · drag to swipe · N: new game · Esc: quit"
        canvas.write(max(0, (cols - len(hint)) // 2), oy + BH + 1, hint, MUTED)


def main():
    app = App(full=True, style=Style(fg="white", bg=BG), title="2048")
    game = Game2048(app)
    app.add(game)
    app.focus(game)
    app.on_key(Key.ESC, lambda: "quit")
    app.on_key("n", game.reset)
    app.on_key("r", game.reset)
    app.run()


if __name__ == "__main__":
    main()
