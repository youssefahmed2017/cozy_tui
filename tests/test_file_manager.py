"""Pure-helper tests for the file-manager example (no filesystem mutation beyond
the pytest tmp_path sandbox)."""

import importlib.util
import pathlib

from cozy_tui import App, Style
from cozy_tui.testing import Harness

_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "examples"
    / "file_manager"
    / "file_manager.py"
)
_spec = importlib.util.spec_from_file_location("file_manager", _PATH)
fm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fm)


def test_human_size():
    assert fm.human_size(0) == "0B"
    assert fm.human_size(512) == "512B"
    assert fm.human_size(1024) == "1.0K"
    assert fm.human_size(1536) == "1.5K"
    assert fm.human_size(1024 * 1024) == "1.0M"
    assert fm.human_size(3 * 1024**3) == "3.0G"


def test_unique_path_returns_original_when_free(tmp_path):
    p = tmp_path / "note.txt"
    assert fm.unique_path(p) == p  # nothing there yet


def test_unique_path_avoids_collisions(tmp_path):
    (tmp_path / "note.txt").write_text("x")
    assert fm.unique_path(tmp_path / "note.txt") == tmp_path / "note (1).txt"
    (tmp_path / "note (1).txt").write_text("x")
    assert fm.unique_path(tmp_path / "note.txt") == tmp_path / "note (2).txt"


def test_unique_path_on_directory_has_no_suffix(tmp_path):
    (tmp_path / "docs").mkdir()
    assert fm.unique_path(tmp_path / "docs") == tmp_path / "docs (1)"


def test_list_dir_sorts_folders_first_then_name(tmp_path):
    (tmp_path / "beta").mkdir()
    (tmp_path / "Alpha").mkdir()
    (tmp_path / "zebra.txt").write_text("z")
    (tmp_path / "apple.txt").write_text("a")
    names = [e.name for e in fm.list_dir(tmp_path)]
    assert names == ["Alpha", "beta", "apple.txt", "zebra.txt"]


def test_entry_reports_dir_size_hidden(tmp_path):
    (tmp_path / "sub").mkdir()
    f = tmp_path / ".secret"
    f.write_text("hello")  # 5 bytes
    entries = {e.name: e for e in fm.list_dir(tmp_path)}
    assert entries["sub"].is_dir is True
    assert entries[".secret"].is_dir is False
    assert entries[".secret"].size == 5
    assert entries[".secret"].hidden is True


def test_up_entry_is_dir_marker():
    up = fm.Entry(pathlib.Path("."), is_up=True)
    assert up.name == ".." and up.is_dir and up.hidden is False


# ── new_entry(): must stay confined to cwd (regression) ─────────────────────


def _manager(start):
    ui = Harness(App(full=False, size="600x200", style=Style(fg="white", bg=fm.BG)))
    manager = fm.FileManager(ui.app, start)
    ui.app.add(manager)
    ui.app.focus(manager)
    ui.settle()  # let the initial background load() finish
    return ui, manager


def _submit_new_entry(ui, manager, name, folder=False):
    manager.new_entry(folder)
    prompt = ui.app._overlays[-1].widget
    prompt.text = name
    prompt.on_key(fm.Key.ENTER)
    ui.settle()  # let load()'s background re-list finish


def test_new_entry_rejects_a_name_that_escapes_the_current_directory(tmp_path):
    # Regression: new_entry() joined the typed name straight onto cwd with
    # no validation -- "../../secret.txt" (or an absolute path) created a
    # file outside the directory being browsed instead of just naming an
    # entry inside it.
    outside = tmp_path / "escaped.txt"
    sub = tmp_path / "sub"
    sub.mkdir()
    ui, manager = _manager(sub)

    _submit_new_entry(ui, manager, "../escaped.txt")

    assert not outside.exists()
    assert "Invalid" in manager.status


def test_new_entry_rejects_a_name_with_a_subdirectory_component(tmp_path):
    ui, manager = _manager(tmp_path)
    _submit_new_entry(ui, manager, "sub/evil.txt")
    assert not (tmp_path / "sub").exists()
    assert "Invalid" in manager.status


def test_new_entry_rejects_dot_and_dotdot(tmp_path):
    ui, manager = _manager(tmp_path)
    _submit_new_entry(ui, manager, "..", folder=True)
    assert "Invalid" in manager.status
    _submit_new_entry(ui, manager, ".", folder=True)
    assert "Invalid" in manager.status


def test_new_entry_still_creates_a_plain_name_in_cwd(tmp_path):
    # The success status ("Created notes.txt") is set right before the
    # subsequent load() overwrites it with "N items" once that reload
    # settles -- existing, unrelated behavior -- so the file's actual
    # presence on disk is the meaningful assertion here.
    ui, manager = _manager(tmp_path)
    _submit_new_entry(ui, manager, "notes.txt")
    assert (tmp_path / "notes.txt").exists()
