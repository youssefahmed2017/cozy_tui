import pytest

from cozy_tui import App, Style
from cozy_tui.events import Key, MouseClick
from cozy_tui.testing import Harness
from cozy_tui.widgets import FilePicker


def make_ui(size="800x300"):
    return Harness(App(full=False, size=size, style=Style(fg="white", bg="black")))


@pytest.fixture
def tree(tmp_path):
    """
    root/
      sub/
        nested.txt
      apple.py
      banana.txt
      zebra.py
    """
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.txt").write_text("x")
    (tmp_path / "apple.py").write_text("x")
    (tmp_path / "banana.txt").write_text("x")
    (tmp_path / "zebra.py").write_text("x")
    return tmp_path


# ── FilePicker (direct, no App) ──────────────────────────────────────────────


def test_lists_dirs_before_files_alphabetically(tree):
    p = FilePicker(tree)
    names_kinds = [(label, kind) for label, _path, kind in p._matches]
    # ".." then "sub" (dir) then the three files, alphabetical within each group
    assert names_kinds == [
        ("..", "up"),
        ("sub", "dir"),
        ("apple.py", "file"),
        ("banana.txt", "file"),
        ("zebra.py", "file"),
    ]


def test_up_entry_omitted_at_filesystem_root(tree):
    root = tree
    while root.parent != root:
        root = root.parent
    p = FilePicker(root)
    assert all(kind != "up" for _l, _p, kind in p._matches)


def test_extensions_filter_only_restricts_files_not_dirs(tree):
    p = FilePicker(tree, extensions=(".py",))
    names = [label for label, _p, kind in p._matches if kind == "file"]
    assert names == ["apple.py", "zebra.py"]
    assert any(kind == "dir" for _l, _p, kind in p._matches)  # "sub" still listed


def test_directory_mode_shows_select_entry_and_no_files(tree):
    p = FilePicker(tree, mode="directory")
    kinds = [kind for _l, _p, kind in p._matches]
    assert kinds[0] == "select"
    assert "file" not in kinds
    assert "dir" in kinds  # "sub" still navigable


def test_search_filters_current_directory_only(tree):
    p = FilePicker(tree)
    for ch in "zeb":
        p.on_key(ch)
    assert [label for label, _p, _k in p._matches] == ["zebra.py"]


def test_query_resets_on_navigation(tree):
    p = FilePicker(tree)
    for ch in "sub":
        p.on_key(ch)
    assert p.query == "sub"
    p.on_key(Key.ENTER)  # navigates into "sub"
    assert p.query == ""
    assert p.cwd == tree / "sub"


def test_enter_on_up_navigates_to_parent(tree):
    p = FilePicker(tree / "sub")
    assert p.cwd == tree / "sub"
    p._move(0)  # ".." is always first when present
    p.on_key(Key.ENTER)
    assert p.cwd == tree


def test_enter_on_a_file_fires_on_select_with_its_path(tree):
    picked = []
    p = FilePicker(tree, on_select=picked.append)
    for ch in "apple":
        p.on_key(ch)
    p.on_key(Key.ENTER)
    assert picked == [tree / "apple.py"]


def test_select_this_folder_fires_on_select_with_cwd(tree):
    picked = []
    p = FilePicker(tree, mode="directory", on_select=picked.append)
    p.on_key(Key.ENTER)  # "· Select this folder ·" is always first
    assert picked == [tree]


def test_unreadable_directory_sets_error_without_crashing(tmp_path):
    missing = tmp_path / "does-not-exist"
    p = FilePicker(missing)
    assert p._error is not None
    assert any(kind == "up" for _l, _p, kind in p._matches)  # can still back out


def test_navigation_clamps_without_wrapping(tree):
    p = FilePicker(tree)
    p.on_key(Key.UP)  # already at 0
    assert p._index == 0
    for _ in range(20):
        p.on_key(Key.DOWN)
    assert p._index == len(p._matches) - 1
    p.on_key(Key.HOME)
    assert p._index == 0
    p.on_key(Key.END)
    assert p._index == len(p._matches) - 1


def test_invalid_mode_raises():
    with pytest.raises(ValueError):
        FilePicker(".", mode="bogus")


# ── App.pick_file() ──────────────────────────────────────────────────────────


def test_pick_file_opens_as_focused_modal(tree):
    ui = make_ui()
    app = ui.app
    picker = app.pick_file(tree)
    assert isinstance(picker, FilePicker)
    assert app._topmost_modal() is not None
    assert app.focused is picker


def test_on_select_fires_and_closes_the_overlay(tree):
    ui = make_ui()
    app = ui.app
    picked = []
    app.pick_file(tree, on_select=picked.append)
    ui.screen
    for ch in "banana":
        ui.press(ch)
    ui.screen
    ui.press(Key.ENTER)
    assert picked == [tree / "banana.txt"]
    assert app._topmost_modal() is None


def test_cancel_fires_on_cancel_not_on_select(tree):
    ui = make_ui()
    app = ui.app
    events = []
    app.pick_file(
        tree,
        on_select=lambda p: events.append(("pick", p)),
        on_cancel=lambda: events.append(("cancel",)),
    )
    app.close_overlay()  # simulates Esc / click-outside dismissal
    assert events == [("cancel",)]


def test_pick_does_not_also_fire_cancel(tree):
    ui = make_ui()
    app = ui.app
    events = []
    app.pick_file(
        tree,
        mode="directory",
        on_select=lambda p: events.append("pick"),
        on_cancel=lambda: events.append("cancel"),
    )
    ui.press(Key.ENTER)  # "Select this folder"
    assert events == ["pick"]


def test_click_on_an_entry_activates_it(tree):
    ui = make_ui()
    app = ui.app
    picked = []
    picker = app.pick_file(tree, on_select=picked.append)
    ui.screen
    # find "apple.py"'s row
    idx = next(i for i, (l, _p, _k) in enumerate(picker._matches) if l == "apple.py")
    row = picker.abs_y + 3 + idx
    ui.click((picker.abs_x + 2, row))
    assert picked == [tree / "apple.py"]
