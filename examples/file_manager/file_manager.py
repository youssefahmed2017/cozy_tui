"""cozy-files — a mouse-and-keyboard TUI file manager.

    python examples/file_manager/file_manager.py [START_DIR]

Navigate with ↑/↓, Enter to open a folder, Backspace to go up. **Right-click**
anywhere for a context menu: Open, Copy path (to the system clipboard), Copy /
Cut / Paste, Rename…, Delete, New ▸ File/Folder, Refresh. Deletes ask for
confirmation; a paste never overwrites (it auto-renames on a name clash).

Shows off nearly the whole toolkit:
  * a fully custom drawing Widget (header bar + scrolling listing + status bar),
  * hover-to-highlight rows (per-widget ``mouse_moves``), click to select,
    double-click / Enter to open,
  * ``RightClickMenu`` with icons, shortcut hints, disabled items and a submenu,
  * ``app.prompt`` for rename / new, and a custom confirm modal for deletes,
  * the built-in clipboard (``clipboard.copy``) for "Copy path",
  * background ``run_worker`` for directory loads and copy/move/delete so the UI
    never blocks.
"""

import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Style, clipboard
from cozy_tui._width import text_width
from cozy_tui.events import Key
from cozy_tui.widget import Widget
from cozy_tui.widgets import Box, Button, Label, MenuItem, MenuSeparator, RightClickMenu

# ── pure helpers (unit-tested in tests/test_file_manager.py) ────────────────────


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "K", "M", "G", "T"):
        if size < 1024 or unit == "T":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}T"


def unique_path(path: Path) -> Path:
    """A non-existing path near ``path`` — appends ' (1)', ' (2)', … on a clash."""
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    i = 1
    while True:
        candidate = path.with_name(f"{stem} ({i}){suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def list_dir(path: Path):
    """Directory entries sorted folders-first, then case-insensitively by name.

    Returns a list of ``Entry``. May raise ``OSError`` (permission denied, …),
    which the caller surfaces via the worker's ``on_error``.
    """
    items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    return [Entry(p) for p in items]


class Entry:
    def __init__(self, path: Path, is_up: bool = False):
        self.path = path
        self.is_up = is_up
        self.name = ".." if is_up else path.name
        if is_up:
            self.is_dir, self.size, self.mtime = True, 0, 0.0
            return
        try:
            st = path.stat()
            self.is_dir = path.is_dir()
            self.size = st.st_size
            self.mtime = st.st_mtime
        except OSError:
            self.is_dir, self.size, self.mtime = False, 0, 0.0

    @property
    def hidden(self) -> bool:
        return not self.is_up and self.name.startswith(".")


# ── styling ─────────────────────────────────────────────────────────────────────

BG = "rgb(24,26,32)"
BAR = "rgb(38,44,58)"
HILITE = "rgb(38,79,120)"

HEADER = Style(fg="bright_white", bg=BAR, styles=["bold"])
FOOTER = Style(fg="bright_white", bg=BAR)
SEL = Style(fg="bright_white", bg=HILITE, styles=["bold"])
SEL_FILL = Style(bg=HILITE)
DIR = Style(fg="bright_cyan")
FILE = Style(fg="white")
DIM = Style(fg="bright_black")

SIZE_W, TIME_W = 9, 16


class FileManager(Widget):
    focusable = True

    def __init__(self, app, start: Path):
        super().__init__(0, 0)
        self.app = app
        self.mouse_moves = True  # hover highlights the row under the cursor
        self.cwd = start.resolve()
        self.entries: list[Entry] = []
        self.index = 0
        self.scroll = 0
        self.status = ""
        self.clip = None  # (op, Path) where op is "copy" or "cut"
        self._rows = self._cols = self._visible = 0
        self.load(self.cwd)

    # ── data / navigation ─────────────────────────────────────────────────────

    @property
    def selected(self):
        return self.entries[self.index] if self.entries else None

    def load(self, path: Path):
        path = Path(path)
        self.status = f"Loading {path}…"

        def done(entries):
            self.cwd = path.resolve()
            up = (
                []
                if self.cwd.parent == self.cwd
                else [Entry(self.cwd.parent, is_up=True)]
            )
            self.entries = up + entries
            self.index = self.scroll = 0
            self.status = f"{len(entries)} item{'s' * (len(entries) != 1)}"
            self.app.invalidate()

        def fail(err):
            self.status = f"Cannot open {path.name or path}: {err}"
            self.app.invalidate()

        self.app.run_worker(lambda: list_dir(path), on_result=done, on_error=fail)

    def _open(self):
        e = self.selected
        if e is None:
            return
        if e.is_dir:
            self.load(e.path)
        else:
            self.status = (
                f"{e.name} — {human_size(e.size)} (files aren't opened in this demo)"
            )

    def _move(self, delta):
        if self.entries:
            self.index = max(0, min(self.index + delta, len(self.entries) - 1))
            self._clamp()

    def _clamp(self):
        vis = max(1, self._visible)
        if self.index < self.scroll:
            self.scroll = self.index
        elif self.index >= self.scroll + vis:
            self.scroll = self.index - vis + 1

    def _index_at(self, row):
        idx = self.scroll + (row - 1)  # row 0 is the header
        if 1 <= row and 0 <= idx < len(self.entries) and row < self._rows - 1:
            return idx
        return None

    # ── operations ────────────────────────────────────────────────────────────

    def copy_path(self):
        if self.selected:
            clipboard.copy(str(self.selected.path))
            self.status = f"Copied path to clipboard: {self.selected.path}"

    def set_clip(self, op):
        e = self.selected
        if e and not e.is_up:
            self.clip = (op, e.path)
            self.status = f"{op.title()}: {e.name} — Paste into a folder to place it"

    def paste(self):
        if not self.clip:
            self.status = "Clipboard is empty (Copy or Cut something first)"
            return
        op, src = self.clip
        src = Path(src)
        dest = unique_path(self.cwd / src.name)
        self.status = f"{'Moving' if op == 'cut' else 'Copying'} {src.name}…"

        def work():
            if op == "copy":
                (shutil.copytree if src.is_dir() else shutil.copy2)(src, dest)
            else:
                shutil.move(str(src), str(dest))
            return dest

        def done(d):
            if op == "cut":
                self.clip = None
            self.status = f"{'Moved' if op == 'cut' else 'Copied'} → {d.name}"
            self.load(self.cwd)

        self.app.run_worker(work, on_result=done, on_error=self._op_error("Paste"))

    def rename(self):
        e = self.selected
        if e is None or e.is_up:
            return

        def submit(new):
            new = new.strip()
            if not new or new == e.name:
                return
            try:
                e.path.rename(e.path.with_name(new))
                self.status = f"Renamed → {new}"
            except OSError as err:
                self.status = f"Rename failed: {err}"
            self.load(self.cwd)

        self.app.prompt(f"Rename '{e.name}' to:", initial=e.name, on_submit=submit)

    def delete(self):
        e = self.selected
        if e is None or e.is_up:
            return
        what = "folder and all its contents" if e.is_dir else "file"
        self._confirm(f"Delete the {what}  '{e.name}' ?", lambda: self._do_delete(e))

    def _do_delete(self, e):
        self.status = f"Deleting {e.name}…"

        def work():
            if e.is_dir:
                shutil.rmtree(e.path)
            else:
                e.path.unlink()

        def done(_):
            self.status = f"Deleted {e.name}"
            self.load(self.cwd)

        self.app.run_worker(work, on_result=done, on_error=self._op_error("Delete"))

    def new_entry(self, folder: bool):
        label = "folder" if folder else "file"

        def submit(name):
            name = name.strip()
            if not name:
                return
            target = self.cwd / name
            try:
                if target.exists():
                    self.status = f"{name} already exists"
                elif folder:
                    target.mkdir()
                    self.status = f"Created {name}/"
                else:
                    target.touch()
                    self.status = f"Created {name}"
            except OSError as err:
                self.status = f"Could not create {label}: {err}"
            self.load(self.cwd)

        self.app.prompt(f"New {label} name:", on_submit=submit)

    def _op_error(self, label):
        def fail(err):
            self.status = f"{label} failed: {err}"
            self.app.invalidate()

        return fail

    # ── overlays ───────────────────────────────────────────────────────────────

    def _confirm(self, message, on_yes):
        box = Box(
            0,
            0,
            "520x110",
            title="Confirm",
            border="bold",
            style=Style(fg="white", bg="black"),
        )
        box.add(Label(2, 1, message))
        box.add(
            Button(2, 3, "Delete", style=Style(fg="white", bg="red")).on_click(
                lambda b: (self.app.close_overlay(box), on_yes())
            )
        )
        box.add(Button(12, 3, "Cancel").on_click(lambda b: self.app.close_overlay(box)))
        self.app.open_overlay(box, close_on_click_outside=True)

    def open_menu(self, col, row):
        idx = self._index_at(row)
        if idx is not None:
            self.index = idx
            self._clamp()
        e = self.selected
        real = e is not None and not e.is_up
        menu = RightClickMenu(
            [
                MenuItem(
                    "Open",
                    icon="📂" if e and e.is_dir else "📄",
                    on_select=lambda i: self._open(),
                    enabled=e is not None,
                ),
                MenuItem(
                    "Copy path",
                    icon="📋",
                    on_select=lambda i: self.copy_path(),
                    enabled=real,
                ),
                MenuSeparator(),
                MenuItem(
                    "Copy", on_select=lambda i: self.set_clip("copy"), enabled=real
                ),
                MenuItem("Cut", on_select=lambda i: self.set_clip("cut"), enabled=real),
                MenuItem(
                    "Paste",
                    on_select=lambda i: self.paste(),
                    enabled=self.clip is not None,
                ),
                MenuSeparator(),
                MenuItem(
                    "Rename…",
                    shortcut="F2",
                    on_select=lambda i: self.rename(),
                    enabled=real,
                ),
                MenuItem(
                    "Delete",
                    icon="🗑",
                    shortcut="Del",
                    on_select=lambda i: self.delete(),
                    enabled=real,
                ),
                MenuSeparator(),
                MenuItem(
                    "New",
                    icon="✨",
                    submenu=[
                        MenuItem(
                            "File…", on_select=lambda i: self.new_entry(folder=False)
                        ),
                        MenuItem(
                            "Folder…", on_select=lambda i: self.new_entry(folder=True)
                        ),
                    ],
                ),
                MenuItem(
                    "Refresh", shortcut="F5", on_select=lambda i: self.load(self.cwd)
                ),
            ]
        )
        menu.open_at(self.app, col, row)

    # ── input ──────────────────────────────────────────────────────────────────

    def on_key(self, key):
        if key == Key.UP:
            self._move(-1)
        elif key == Key.DOWN:
            self._move(1)
        elif key == Key.PAGE_UP:
            self._move(-max(1, self._visible - 1))
        elif key == Key.PAGE_DOWN:
            self._move(max(1, self._visible - 1))
        elif key == Key.HOME:
            self._move(-len(self.entries))
        elif key == Key.END:
            self._move(len(self.entries))
        elif key == Key.ENTER:
            self._open()
        elif key == Key.BACKSPACE:
            if self.cwd.parent != self.cwd:
                self.load(self.cwd.parent)
        elif key == Key.DELETE:
            self.delete()
        elif key == Key.F2:
            self.rename()
        elif key == Key.F5:
            self.load(self.cwd)

    def contains(self, col, row):
        return True  # the only widget — take clicks/hover anywhere on screen

    def on_mouse_move(self, col=None, row=None):
        idx = self._index_at(row)
        if idx is not None:
            self.index = idx

    def on_mouse_click(self, col=None, row=None):
        idx = self._index_at(row)
        if idx is not None:
            self.index = idx

    def on_mouse_double_click(self, col=None, row=None):
        idx = self._index_at(row)
        if idx is not None:
            self.index = idx
            self._open()

    # ── drawing ────────────────────────────────────────────────────────────────

    def natural_width(self, scale):
        return self._cols or 40

    def natural_height(self, scale):
        return self._rows or 10

    def _clip_name(self, name, width):
        if text_width(name) <= width:
            return name
        out = ""
        for ch in name:
            if text_width(out + ch) > width - 1:
                break
            out += ch
        return out + "…"

    def draw(self, canvas):
        self._cols, self._rows = canvas.cols, canvas.rows
        self._visible = max(1, self._rows - 2)
        self._clamp()
        cols = self._cols

        # header: breadcrumb, right-trimmed to fit
        path = str(self.cwd)
        avail = cols - 4
        if text_width(path) > avail:
            path = "…" + path[-(avail - 1) :]
        canvas.write(0, 0, " " * cols, HEADER)
        canvas.write(1, 0, f"📂 {path}", HEADER)

        # listing
        for i in range(self._visible):
            idx = self.scroll + i
            y = 1 + i
            if idx >= len(self.entries):
                canvas.write(0, y, " " * cols, self.style)
                continue
            e = self.entries[idx]
            sel = idx == self.index
            fill = SEL_FILL if sel else self.style
            if sel:
                text = SEL
            elif e.is_dir:
                text = DIR
            elif e.hidden:
                text = DIM
            else:
                text = FILE
            canvas.write(0, y, " " * cols, fill)

            icon = "↩ " if e.is_up else ("📁" if e.is_dir else "📄")
            canvas.write(1, y, icon, text)
            size_str = "" if e.is_dir else human_size(e.size)
            time_str = (
                ""
                if e.is_up
                else time.strftime("%Y-%m-%d %H:%M", time.localtime(e.mtime))
            )
            name_w = cols - 4 - SIZE_W - TIME_W - 2
            canvas.write(4, y, self._clip_name(e.name, name_w), text)
            canvas.write(cols - TIME_W - SIZE_W - 2, y, size_str.rjust(SIZE_W), text)
            canvas.write(cols - TIME_W - 1, y, time_str.rjust(TIME_W), text)

        # footer: status on the left, position + clipboard on the right
        fy = self._rows - 1
        canvas.write(0, fy, " " * cols, FOOTER)
        left = (
            self.status or "Enter: open · Backspace: up · right-click: menu · Esc: quit"
        )
        canvas.write(1, fy, self._clip_name(left, cols - 22), FOOTER)
        pos = f"{self.index + 1}/{len(self.entries)}" if self.entries else "0/0"
        if self.clip:
            pos = f"[{self.clip[0]}] " + pos
        canvas.write(cols - text_width(pos) - 1, fy, pos, FOOTER)


def main():
    start = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    if not start.is_dir():
        print(f"Not a directory: {start}")
        return
    app = App(full=True, style=Style(fg="white", bg=BG), title="cozy-files")
    fm = FileManager(app, start)
    app.add(fm)
    app.focus(fm)
    app.on_right_click(lambda col, row, w: fm.open_menu(col, row))
    app.on_key(Key.ESC, lambda: "quit")
    app.run()


if __name__ == "__main__":
    main()
