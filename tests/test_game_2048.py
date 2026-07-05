"""Pure game-logic tests for the 2048 example (examples/game_2048/game_2048.py)."""

import importlib.util
import pathlib
import random

_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "examples" / "game_2048" / "game_2048.py"
)
_spec = importlib.util.spec_from_file_location("game_2048", _PATH)
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)


def test_slide_merges_equal_pair_once():
    assert g._slide_row([2, 2, 2, 2]) == ([4, 4, 0, 0], 8)
    assert g._slide_row([2, 2, 4, 0]) == ([4, 4, 0, 0], 4)
    assert g._slide_row([4, 0, 0, 4]) == ([8, 0, 0, 0], 8)
    assert g._slide_row([0, 0, 0, 0]) == ([0, 0, 0, 0], 0)
    assert g._slide_row([2, 0, 2, 2]) == ([4, 2, 0, 0], 4)  # leftmost pair merges


def test_move_left_and_right_are_mirror_images():
    grid = [[2, 2, 0, 0], [0, 4, 4, 0], [0, 0, 0, 0], [8, 0, 8, 0]]
    left, gained_l, moved_l = g.move(grid, "left")
    assert moved_l and gained_l == 4 + 8 + 16
    assert left[0] == [4, 0, 0, 0]
    assert left[1] == [8, 0, 0, 0]
    assert left[3] == [16, 0, 0, 0]
    right, _gained_r, _moved = g.move(grid, "right")
    assert right[0] == [0, 0, 0, 4]
    assert right[3] == [0, 0, 0, 16]


def test_move_up_and_down():
    grid = [[2, 0, 0, 0], [2, 0, 0, 0], [4, 0, 0, 0], [4, 0, 0, 0]]
    up, gained, moved = g.move(grid, "up")
    assert moved and gained == 12
    assert [row[0] for row in up] == [4, 8, 0, 0]
    down, _g, _m = g.move(grid, "down")
    assert [row[0] for row in down] == [0, 0, 4, 8]


def test_move_reports_not_moved_when_nothing_changes():
    grid = [[2, 4, 8, 16], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    new, gained, moved = g.move(grid, "left")
    assert not moved and gained == 0 and new == grid


def test_move_does_not_mutate_input():
    grid = [[2, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    snapshot = [row[:] for row in grid]
    g.move(grid, "left")
    assert grid == snapshot  # move returns a new grid, leaves the original alone


def test_has_moves():
    assert g.has_moves([[2, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    # full board with an adjacent equal pair is still playable
    assert g.has_moves([[2, 2, 4, 8], [16, 32, 64, 128], [2, 4, 8, 16], [32, 64, 128, 256]])
    # full board, no two equal neighbors -> stuck
    stuck = [[2, 4, 2, 4], [4, 2, 4, 2], [2, 4, 2, 4], [4, 2, 4, 2]]
    assert not g.has_moves(stuck)


def test_spawn_fills_one_empty_cell_with_2_or_4():
    grid = g.new_grid()
    cell = g.spawn(grid, random.Random(0))
    r, c = cell
    assert grid[r][c] in (2, 4)
    assert sum(v != 0 for row in grid for v in row) == 1


def test_spawn_returns_none_on_full_board():
    full = [[2, 4, 2, 4], [4, 2, 4, 2], [2, 4, 2, 4], [4, 2, 4, 2]]
    assert g.spawn(full, random.Random(0)) is None


def test_max_tile():
    assert g.max_tile([[2, 4, 8, 16], [0, 0, 0, 2048], [0, 0, 0, 0], [0, 0, 0, 0]]) == 2048
