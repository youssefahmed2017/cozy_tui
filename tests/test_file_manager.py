"""Pure-helper tests for the file-manager example (no filesystem mutation beyond
the pytest tmp_path sandbox)."""

import importlib.util
import pathlib

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
