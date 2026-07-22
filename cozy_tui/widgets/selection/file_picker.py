from pathlib import Path

from cozy_tui.style import Style, selection_style
from cozy_tui.widget import Widget
from cozy_tui.widgets.selection._search_palette import (
    _SearchPaletteMixin,
    draw_panel_frame,
)

_SELECT_DIR = "· Select this folder ·"
_UP = ".."

_ICONS = {"select": "📌", "up": "⬆", "dir": "📁", "file": "📄"}


def _safe_is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:
        return False


class FilePicker(_SearchPaletteMixin, Widget):
    """A directory-browsing file/folder picker, shown as a modal overlay via
    ``App.pick_file()``. Type to filter entries *in the current directory*
    (like :class:`~cozy_tui.widgets.selection.theme_palette.ThemePalette`/
    :class:`~cozy_tui.widgets.selection.command_palette.CommandPalette`);
    Up/Down/Home/End move the cursor; Enter or a click on a directory (or
    ``..``) navigates into it, on a file (``mode="file"``) picks it. Esc /
    click-outside cancel (handled by the overlay layer).

    ``mode="directory"`` shows a "Select this folder" entry instead of
    listing files, for picking a directory itself rather than descending
    into one forever. ``extensions`` (e.g. ``(".py", ".md")``) restricts
    which files are shown in file mode. A directory that can't be listed
    (permissions, race with something deleting it, ...) shows a dimmed
    message instead of crashing; the picker just stays where it was.

    Self-contained: draws its own bordered panel, so it needs no surrounding
    ``Box`` -- the same approach as every other palette/dialog in this
    library.
    """

    focusable = True

    def __init__(
        self,
        start_dir=None,
        *,
        mode: str = "file",
        extensions=None,
        on_select=None,
        width: int = 60,
        height: int = 10,
        style=None,
    ):
        super().__init__(0, 0, style or Style(fg="white", bg="black"))
        if mode not in ("file", "directory"):
            raise ValueError('mode must be "file" or "directory"')
        self.mode = mode
        self.extensions = tuple(e.lower() for e in extensions) if extensions else None
        self.on_select = on_select
        self.query = ""
        self.width = max(30, width)
        self.height = max(1, height)  # max visible entries
        self._error: str | None = None
        self._all: list = []  # [(label, path, kind)]
        self._matches: list = []
        self._index = 0
        self._scroll_off = 0
        self.cwd = Path(start_dir or Path.cwd()).resolve()
        self._load()

    # ── directory listing / filtering / activation ───────────────────────────

    def _load(self) -> None:
        """(Re)list `self.cwd`'s contents into `_all`, resetting the search
        query -- a filter scoped to the old directory shouldn't silently
        carry over to the new one."""
        self._error = None
        entries = []
        # Guards against a start_dir (or a stale self.cwd after something
        # external deletes it) that isn't actually a directory -- otherwise
        # this entry would still be clickable and hand a non-directory Path
        # to on_select.
        if self.mode == "directory" and _safe_is_dir(self.cwd):
            entries.append((_SELECT_DIR, self.cwd, "select"))
        if self.cwd.parent != self.cwd:  # not the filesystem root
            entries.append((_UP, self.cwd.parent, "up"))

        try:
            children = list(self.cwd.iterdir())
        except OSError:
            self._error = "cannot access this folder"
            children = []

        rows = []
        for p in children:
            if _safe_is_dir(p):
                rows.append((p.name, p, "dir"))
            elif self.mode == "file":
                if self.extensions and p.suffix.lower() not in self.extensions:
                    continue
                rows.append((p.name, p, "file"))
        rows.sort(key=lambda r: (r[2] != "dir", r[0].lower()))
        entries.extend(rows)

        self._all = entries
        self.query = ""
        self._refilter()

    def _matches_query(self, item, query: str) -> bool:
        label, _path, _kind = item
        return query in label.lower()

    def _activate_item(self, item) -> None:
        _label, path, kind = item
        if kind in ("up", "dir"):
            self.cwd = path
            self._load()
        elif kind in ("select", "file") and self.on_select is not None:
            self.on_select(path)

    # ── Widget interface ──────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        return self.width + 2  # + left/right border

    def natural_height(self, scale) -> int:
        rows = min(self.height, max(1, len(self._matches)))
        return rows + 5  # + top border, path row, search row, hint row, bottom border

    def contains(self, col: int, row: int) -> bool:
        return self.abs_x <= col < self.abs_x + self.natural_width(
            1
        ) and self.abs_y <= row < self.abs_y + self.natural_height(1)

    def on_mouse_click(self, col=None, row=None) -> None:
        if row is None:
            return
        list_top = self.abs_y + 3  # border + path row + search row
        idx = self._scroll_off + (row - list_top)
        if 0 <= idx < len(self._matches):
            self._index = idx
            self._activate()

    def draw(self, canvas) -> None:
        from cozy_tui.theme import get_theme  # local: theme.py builds on Style

        raw_bg = self.style.raw_bg
        border = Style(fg=get_theme().accent, bg=raw_bg, styles=["bold"])
        dim = Style(fg="bright_black", bg=raw_bg)
        x, y, w = self.abs_x, self.abs_y, self.width
        h = self.natural_height(1)
        draw_panel_frame(canvas, x, y, w, h, border, self.style)

        path_text = str(self.cwd)
        if len(path_text) > w:
            path_text = "…" + path_text[-(w - 1) :]
        canvas.write(x + 1, y + 1, path_text.ljust(w)[:w], dim)

        search = f"🔍 {self.query}▏".ljust(w)[:w]
        canvas.write(x + 1, y + 2, search, self.style)

        if self._error:
            canvas.write(x + 1, y + 3, f"  ({self._error})".ljust(w)[:w], dim)
            visible = 1
        elif not self._matches:
            canvas.write(x + 1, y + 3, "  no matching entries".ljust(w)[:w], dim)
            visible = 1
        else:
            visible = min(self.height, len(self._matches))
            for row in range(visible):
                idx = self._scroll_off + row
                label, _path, kind = self._matches[idx]
                text = f"  {_ICONS[kind]} {label}"
                style = selection_style() if idx == self._index else self.style
                canvas.write(x + 1, y + 3 + row, text.ljust(w)[:w], style)

        hint = "  Enter/click: open" + (" / select" if self.mode == "directory" else "")
        hint += " · Esc: cancel"
        canvas.write(x + 1, y + 3 + visible, hint.ljust(w)[:w], dim)
