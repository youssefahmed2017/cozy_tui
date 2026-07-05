"""Snake — a real-time game in the terminal.

Arrow keys steer; eat the food (●) to grow; don't hit the walls or yourself.
Shows off:
  * a real-time loop via app.tick_interval (logic decoupled from render rate),
  * a fully custom drawing Widget that paints the play field cell-by-cell,
  * a "Game Over" modal overlay (no light-dismiss — you must choose Restart/Quit).
"""

import sys
import time
from collections import deque
from pathlib import Path
from random import randrange

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Style
from cozy_tui.events import Key
from cozy_tui.widget import Widget
from cozy_tui.widgets import Box, Button, Label

WALL = Style(fg="bright_black")
BODY = Style(fg="green")
HEAD = Style(fg="bright_green", styles=["bold"])
FOOD = Style(fg="bright_red", styles=["bold"])
TITLE = Style(fg="bright_cyan", styles=["bold"])

STEP = 0.11  # seconds per move


class Snake(Widget):
    focusable = True

    def __init__(self, app, x, y, w, h):
        super().__init__(x, y)
        self.app = app
        self.w = w
        self.h = h
        self._over_box = None
        self.reset()

    def reset(self):
        cx, cy = self.w // 2, self.h // 2
        self.body = deque([(cx - 1, cy), (cx, cy)])  # last item is the head
        self.cells = set(self.body)
        self.dir = (1, 0)
        self._next_dir = (1, 0)
        self.score = 0
        self.alive = True
        self._last_step = time.monotonic()
        self._place_food()
        if self._over_box is not None:
            self.app.close_overlay(self._over_box)
            self._over_box = None

    def _place_food(self):
        free = [
            (fx, fy)
            for fy in range(self.h)
            for fx in range(self.w)
            if (fx, fy) not in self.cells
        ]
        self.food = free[randrange(len(free))] if free else None

    # ── input ─────────────────────────────────────────────────────────────────

    def on_key(self, key):
        turns = {
            Key.UP: (0, -1),
            Key.DOWN: (0, 1),
            Key.LEFT: (-1, 0),
            Key.RIGHT: (1, 0),
        }
        if key in turns:
            dx, dy = turns[key]
            # ignore a 180° reversal into your own neck
            if (dx, dy) != (-self.dir[0], -self.dir[1]):
                self._next_dir = (dx, dy)

    # ── simulation (called from draw, gated by wall-clock) ──────────────────────

    def _step(self):
        self.dir = self._next_dir
        hx, hy = self.body[-1]
        nx, ny = hx + self.dir[0], hy + self.dir[1]
        eating = (nx, ny) == self.food
        occupied = self.cells if eating else self.cells - {self.body[0]}
        if nx < 0 or nx >= self.w or ny < 0 or ny >= self.h or (nx, ny) in occupied:
            self._game_over()
            return
        self.body.append((nx, ny))
        self.cells.add((nx, ny))
        if eating:
            self.score += 1
            self._place_food()
        else:
            self.cells.discard(self.body.popleft())

    def _game_over(self):
        self.alive = False
        box = Box(0, 0, "340x110", title="Game Over", border="bold")
        box.add(Label(2, 1, f"Score: {self.score}"))
        box.add(Button(2, 3, "Restart").on_click(lambda b: self.reset()))
        box.add(Button(14, 3, "Quit").on_click(lambda b: self.app.quit()))
        self._over_box = box
        # Force a deliberate choice: no Esc / click-outside dismissal.
        self.app.open_overlay(box, close_on_escape=False, close_on_click_outside=False)

    # ── Widget interface ───────────────────────────────────────────────────────

    def natural_width(self, scale):
        return self.w + 2

    def natural_height(self, scale):
        return self.h + 2

    def draw(self, canvas):
        if self.alive:
            now = time.monotonic()
            if now - self._last_step >= STEP:
                self._step()
                self._last_step = now

        x, y, w, h = self.abs_x, self.abs_y, self.w, self.h
        title = f" Snake — score {self.score} "
        top = "┏" + title.center(w, "━")[:w] + "┓"
        canvas.write(x, y, top, WALL)
        canvas.write(x, y + h + 1, "┗" + "━" * w + "┛", WALL)
        for r in range(h):
            canvas.write(x, y + 1 + r, "┃", WALL)
            canvas.write(x + w + 1, y + 1 + r, "┃", WALL)

        if self.food is not None:
            fx, fy = self.food
            canvas.write(x + 1 + fx, y + 1 + fy, "●", FOOD)
        for i, (bx, by) in enumerate(self.body):
            head = i == len(self.body) - 1
            canvas.write(x + 1 + bx, y + 1 + by, "█", HEAD if head else BODY)


def main():
    app = App(full=True, style=Style(fg="white", bg="black"))
    app.tick_interval = 0.04  # render ~25fps; the snake steps every STEP seconds

    w = min(44, max(20, app.cols - 6))
    h = min(20, max(10, app.rows - 5))
    gx = max(1, (app.cols - (w + 2)) // 2)
    gy = max(2, (app.rows - (h + 2)) // 2)

    app.add(
        Label(
            2,
            0,
            "SNAKE — arrow keys to steer, eat ●, avoid walls & yourself. Esc: quit",
            TITLE,
        )
    )
    game = Snake(app, gx, gy, w, h)
    app.add(game)
    app.focus(game)
    app.on_key(Key.ESC, lambda: "quit")
    app.run()


if __name__ == "__main__":
    main()
