"""DropFilesArea: path parsing, ingest/copy/move, collisions, and rendering."""

import os

from cozy_tui import App, Style
from cozy_tui.events import Paste
from cozy_tui.widgets import DropFilesArea
from cozy_tui.widgets.input.drop_files_area import parse_dropped_paths


# ── path parsing ──────────────────────────────────────────────────────────────


def test_parse_plain_and_multiple_paths():
    assert parse_dropped_paths("/home/u/a.txt") == ["/home/u/a.txt"]
    assert parse_dropped_paths("/a/one.txt /b/two.txt") == ["/a/one.txt", "/b/two.txt"]


def test_parse_file_uri_percent_decoded_and_multiple():
    assert parse_dropped_paths("file:///home/u/a%20b.png") == ["/home/u/a b.png"]
    assert parse_dropped_paths(
        "file:///a/b.txt\nfile:///c/d.txt"
    ) == ["/a/b.txt", "/c/d.txt"]


def test_parse_windows_file_uri_strips_leading_slash():
    assert parse_dropped_paths("file:///C:/Users/me/a.png") == ["C:/Users/me/a.png"]


def test_parse_quoted_paths_with_spaces():
    assert parse_dropped_paths('"/home/u/my file.txt"') == ["/home/u/my file.txt"]
    assert parse_dropped_paths("'/home/u/my file.txt'") == ["/home/u/my file.txt"]


def test_parse_backslash_escaped_spaces_posix():
    assert parse_dropped_paths(r"/home/u/my\ file.txt") == ["/home/u/my file.txt"]


def test_parse_windows_backslash_path_is_preserved():
    assert parse_dropped_paths(r"C:\Users\me\file.png") == [r"C:\Users\me\file.png"]


def test_parse_expands_tilde_and_ignores_empty():
    assert parse_dropped_paths("~/x.txt") == [os.path.expanduser("~/x.txt")]
    assert parse_dropped_paths("   ") == []


# ── ingest (runs inline when there is no App event loop) ────────────────────────


def test_drop_copies_file_and_fires_on_drop(tmp_path):
    src = tmp_path / "photo.png"
    src.write_bytes(b"pixels")
    store = tmp_path / "uploads"
    seen = []
    da = DropFilesArea(0, 0, store, "200x80", on_drop=seen.append)

    da.on_key(Paste(str(src)))

    assert (store / "photo.png").read_bytes() == b"pixels"
    assert src.exists()  # copy leaves the original in place
    assert seen and [p.name for p in seen[0]] == ["photo.png"]
    assert da._recent == ["photo.png"]


def test_drop_never_overwrites_auto_renames(tmp_path):
    src = tmp_path / "note.txt"
    src.write_text("new")
    store = tmp_path / "store"
    store.mkdir()
    (store / "note.txt").write_text("existing")
    da = DropFilesArea(0, 0, store, "200x80")

    da._ingest(str(src))

    assert (store / "note.txt").read_text() == "existing"      # untouched
    assert (store / "note (1).txt").read_text() == "new"       # dropped copy


def test_move_relocates_source(tmp_path):
    src = tmp_path / "doc.md"
    src.write_text("body")
    store = tmp_path / "moved"
    da = DropFilesArea(0, 0, store, "200x80", move=True)

    da._ingest(str(src))

    assert (store / "doc.md").read_text() == "body"
    assert not src.exists()  # move removes the original


def test_typed_path_is_filed_on_enter(tmp_path):
    """Terminals that type a dropped path as raw chars (no bracketed paste) are
    handled by buffering the characters and filing on Enter."""
    from cozy_tui.events import Key

    src = tmp_path / "raw.txt"
    src.write_text("data")
    store = tmp_path / "store"
    da = DropFilesArea(0, 0, store, "200x80")

    for ch in str(src):  # simulate the terminal typing the path character-by-character
        da.on_key(ch)
    assert not (store / "raw.txt").exists()  # nothing filed until Enter
    da.on_key(Key.ENTER)

    assert (store / "raw.txt").read_bytes() == b"data"
    assert da._pending == ""  # buffer cleared after filing


def test_enter_with_empty_buffer_is_a_noop(tmp_path):
    from cozy_tui.events import Key

    da = DropFilesArea(0, 0, tmp_path / "store", "200x80")
    da.on_key(Key.ENTER)
    assert da._status == "" and not (tmp_path / "store").exists()


def test_backspace_edits_the_buffer(tmp_path):
    from cozy_tui.events import Key

    da = DropFilesArea(0, 0, tmp_path / "store", "200x80")
    for ch in "abc":
        da.on_key(ch)
    da.on_key(Key.BACKSPACE)
    assert da._pending == "ab"


def test_missing_path_reports_error_without_raising(tmp_path):
    store = tmp_path / "store"
    da = DropFilesArea(0, 0, store, "200x80")

    da._ingest(str(tmp_path / "ghost.txt"))  # never created

    assert da._error
    assert "Not found" in da._status
    assert not store.exists()  # nothing written


def test_unreadable_drop_text_reports_error(tmp_path):
    da = DropFilesArea(0, 0, tmp_path / "store", "200x80")
    da._ingest("   ")
    assert da._error and "path" in da._status.lower()


# ── rendering ──────────────────────────────────────────────────────────────────


def test_draw_shows_hint_and_focus_state():
    app = App(full=False, size="800x300", style=Style(fg="white", bg="black"))
    da = DropFilesArea(0, 0, "uploads/", "400x120")
    app.add(da)

    snap = app.snapshot()
    assert "Drop files here" in snap
    assert "click / Tab to focus" in snap  # unfocused hint

    app.focus(da)
    snap = app.snapshot()
    assert "Drop files here" in snap
    assert "click / Tab to focus" not in snap  # focused: hint swaps out


def test_dock_resize_sets_cell_size():
    da = DropFilesArea(0, 0, "store", "100x100")
    da.dock_resize(50, 20, 10)
    assert da.natural_width(10) == 50
    assert da.natural_height(10) == 20
