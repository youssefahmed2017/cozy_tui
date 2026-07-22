"""A drop-a-file zone.

A terminal never hands a program a *file* on a drag-and-drop — it types the
file's **path** into the input stream, almost always as a bracketed paste
(``ESC[200~ … ESC[201~``), which Cozy TUI already parses into a
:class:`~cozy_tui.events.Paste` event. So :class:`DropFilesArea` is a focusable
zone that reads that paste, resolves the path(s) on the local filesystem, and
copies them into ``storage_location`` (``move=True`` relocates instead).

Because it works off the *path text*, a file dropped from another machine (an
SSH session, say) refers to the terminal's filesystem, not the process's — that
case is surfaced as a friendly "not found here" status rather than a crash. The
same paste path also arrives if the user pastes a path with the keyboard, so the
zone doubles as a "paste a path here" target.
"""

import os
import re
import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse

from cozy_tui._width import clip_text, tail_clip_text, text_width
from cozy_tui.events import Key, Paste
from cozy_tui.style import Style
from cozy_tui.widget import Widget

# ── path parsing (pure, unit-tested in tests/test_drop_files_area.py) ────────────


def _from_file_uri(uri: str) -> str:
    """``file:///home/u/a%20b.png`` → ``/home/u/a b.png`` (and strip the leading
    slash off a Windows ``file:///C:/…`` drive path)."""
    path = unquote(urlparse(uri).path)
    if re.match(r"^/[A-Za-z]:", path):  # /C:/Users/… → C:/Users/…
        path = path[1:]
    return path


def _tokenize(text: str) -> list[str]:
    """Split a run of paths honoring quotes and backslash-escaped spaces, without
    treating Windows path separators (``\\``) as escapes."""
    tokens, cur, quote, i = [], [], None, 0
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == quote:
                quote = None
            else:
                cur.append(ch)
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "\\" and i + 1 < len(text) and text[i + 1].isspace():
            cur.append(text[i + 1])  # backslash-escaped whitespace → literal
            i += 1
        elif ch.isspace():
            if cur:
                tokens.append("".join(cur))
                cur = []
        else:
            cur.append(ch)
        i += 1
    if cur:
        tokens.append("".join(cur))
    return tokens


def parse_dropped_paths(text: str) -> list[str]:
    """Normalize the text of a file drop (or path paste) into filesystem paths.

    Handles ``file://`` URIs (percent-decoded, possibly several), single/double
    quoting, backslash-escaped spaces, and ``~`` expansion. Returns the raw path
    strings in the order they appeared; existence is the caller's concern.
    """
    text = text.strip()
    if not text:
        return []
    if "file://" in text:
        return [_from_file_uri(u) for u in re.findall(r"file://\S+", text)]
    return [os.path.expanduser(t) for t in _tokenize(text) if t]


def _unique_path(path: Path, reserved=frozenset()) -> Path:
    """A non-existing, unreserved path near ``path`` — appends ' (1)', ' (2)',
    … on a clash, so a drop never overwrites an existing file. ``reserved``
    additionally excludes destinations already claimed by an in-flight
    copy/move that hasn't reached disk yet (see ``DropFilesArea._ingest``) --
    without it, two drops of a same-named file arriving close enough
    together could both resolve to the same destination before either
    worker's copy finishes, and one would silently clobber the other."""
    stem, suffix = path.stem, path.suffix
    candidate = path
    i = 1
    while candidate.exists() or candidate in reserved:
        candidate = path.with_name(f"{stem} ({i}){suffix}")
        i += 1
    return candidate


# ── widget ───────────────────────────────────────────────────────────────────────


class DropFilesArea(Widget):
    """A focusable drop zone that copies dropped/pasted files into a directory.

    Drop a file onto the terminal (or paste its path) while this zone has focus:
    the path is resolved on the local filesystem and copied into
    ``storage_location`` (created if missing), never overwriting — a name clash
    auto-renames to ``name (1)``. ``on_drop`` fires with the list of stored
    :class:`~pathlib.Path` s.

    ``size`` is a ``"WIDTHxHEIGHT"`` string in virtual pixels (÷ ``App.SCALE`` for
    cells), like :class:`Box`; a docked ``DropFilesArea`` fills its slice instead.

    ``accept`` filters by extension (``".png"`` or ``"png"``, either works;
    case-insensitive) — a dropped file whose suffix doesn't match is rejected
    rather than stored. For anything an extension list can't express (size,
    content, a filename pattern, …), register :meth:`on_validate` instead; if
    both are set, a file must pass both to be accepted.

    Example::

        drop = DropFilesArea(2, 2, "uploads/", "400x120", accept=[".png", ".jpg"])
        drop.on_drop(lambda paths: status.set(f"stored {len(paths)}"))
        app.add(drop)
    """

    focusable = True
    _MAX_RECENT = 4

    def __init__(
        self,
        x,
        y,
        storage_location,
        size,
        *,
        move=False,
        hint=None,
        accept=None,
        on_drop=None,
        style=None,
        accent="bright_cyan",
    ):
        super().__init__(x, y, style)
        self.storage_location = Path(storage_location)
        self.width, self.height = map(int, size.split("x"))
        self.move = move
        self.hint = hint or ("Drop files to move here" if move else "Drop files here")
        self.accent = accent
        # Normalize so both ".png" and "png" work; compared case-insensitively
        # against Path.suffix (which is always "" or ".xxx").
        self.accept = (
            [e if e.startswith(".") else f".{e}" for e in accept] if accept else None
        )
        self._accept_set = {e.lower() for e in self.accept} if self.accept else None
        self._validate = None
        self._on_drop = on_drop
        self._status = ""
        self._error = False
        self._recent: list[str] = []  # names of the most recently stored files
        self._pending = ""  # path text typed / raw-dropped, filed on Enter
        self._app = None  # set to the canvas (App) each draw, for workers/redraw
        self._wc = self._hc = 0
        # Destinations claimed by a copy/move that's started but not finished
        # yet -- only ever touched from the main thread (_ingest, and the
        # run_worker on_result/on_error callbacks, which the App always fires
        # on the main thread), so no lock is needed.
        self._reserved: set = set()

    def on_drop(self, func):
        """Register a callback fired after a successful drop. Receives the list of
        stored :class:`~pathlib.Path` s."""
        self._on_drop = func
        return self

    def on_validate(self, func):
        """Register a custom validator called with each dropped file's
        :class:`~pathlib.Path` (before it's copied/moved); return a falsy value
        to reject it. Composes with ``accept`` — both must pass if both are set."""
        self._validate = func
        return self

    def _accepts(self, path: Path) -> bool:
        if self._accept_set is not None and path.suffix.lower() not in self._accept_set:
            return False
        if self._validate is not None:
            return bool(self._validate(path))
        return True

    # ── ingest ───────────────────────────────────────────────────────────────────

    def on_key(self, key):
        # A drop that arrives as a bracketed paste is filed immediately. Some
        # terminals instead *type* the dropped path as raw characters (no paste
        # markers) — those are buffered and filed when the user presses Enter,
        # which also lets a path be pasted/typed by hand.
        if isinstance(key, Paste):
            self._pending = ""
            self._ingest(key.text)
        elif key == Key.ENTER:
            text, self._pending = self._pending, ""
            if text.strip():
                self._ingest(text)
        elif key == Key.BACKSPACE:
            self._pending = self._pending[:-1]
            self._redraw()
        elif isinstance(key, str) and key.isprintable():
            self._pending += key
            self._redraw()

    def _redraw(self):
        if self._app is not None:
            self._app.invalidate()

    def _ingest(self, text):
        paths = [Path(p) for p in parse_dropped_paths(text)]
        if not paths:
            self._set_status("Couldn't read a file path from that drop", error=True)
            return
        found = [p for p in paths if p.exists()]
        missing = [p for p in paths if not p.exists()]
        if not found:
            names = ", ".join(p.name for p in missing) or "that file"
            self._set_status(f"Not found on this machine: {names}", error=True)
            return

        accepted, rejected = [], []
        for p in found:
            (accepted if self._accepts(p) else rejected).append(p)
        if not accepted:
            names = ", ".join(p.name for p in rejected) or "that file"
            self._set_status(f"Rejected (not an accepted type): {names}", error=True)
            return

        self._set_status(
            f"{'Moving' if self.move else 'Copying'} {len(accepted)} "
            f"file{'s' * (len(accepted) != 1)}…"
        )
        try:
            self.storage_location.mkdir(parents=True, exist_ok=True)
        except OSError as err:
            self._set_status(
                f"Can't write to {self.storage_location}: {err}", error=True
            )
            return

        # Resolved and reserved here, on the main thread, before any worker
        # starts -- not inside work() on the background thread, where two
        # concurrent drops of a same-named file could both see the same
        # not-yet-existing destination and race to write it.
        dest_pairs = []
        for src in accepted:
            dest = _unique_path(self.storage_location / src.name, self._reserved)
            self._reserved.add(dest)
            dest_pairs.append((src, dest))

        def work():
            stored = []
            for src, dest in dest_pairs:
                if self.move:
                    shutil.move(str(src), str(dest))
                elif src.is_dir():
                    shutil.copytree(src, dest)
                else:
                    shutil.copy2(src, dest)
                stored.append(dest)
            return stored

        def done(stored):
            self._reserved.difference_update(dest for _src, dest in dest_pairs)
            self._recent = [p.name for p in stored] + self._recent
            del self._recent[self._MAX_RECENT :]
            verb = "Moved" if self.move else "Copied"
            notes = []
            if missing:
                notes.append(f"{len(missing)} not found")
            if rejected:
                notes.append(f"{len(rejected)} rejected")
            extra = f"  ({', '.join(notes)})" if notes else ""
            self._set_status(f"{verb} {len(stored)} → {self.storage_location}{extra}")
            self._fire_change(stored)
            if self._on_drop:
                self._on_drop(stored)

        def fail(err):
            self._reserved.difference_update(dest for _src, dest in dest_pairs)
            self._set_status(
                f"{'Move' if self.move else 'Copy'} failed: {err}", error=True
            )

        if self._app is not None:
            self._app.run_worker(work, on_result=done, on_error=fail)
        else:  # no event loop (e.g. a headless test) — run inline
            try:
                done(work())
            except OSError as err:
                fail(err)

    def _set_status(self, message, *, error=False):
        self._status = message
        self._error = error
        if self._app is not None:
            self._app.invalidate()

    # ── framework hooks ──────────────────────────────────────────────────────────

    def natural_width(self, scale):
        return self.width // scale

    def natural_height(self, scale):
        return self.height // scale

    def dock_resize(self, w, h, scale):
        self.width = w * scale
        self.height = h * scale

    def contains(self, col, row):
        return (
            self.abs_x <= col < self.abs_x + self._wc
            and self.abs_y <= row < self.abs_y + self._hc
        )

    def _center(self, canvas, y, text, style):
        if not (0 <= y < self._hc):
            return
        text = clip_text(text, self._wc - 2)
        cx = self.abs_x + max(1, (self._wc - text_width(text)) // 2)
        canvas.write(cx, self.abs_y + y, text, style)

    def draw(self, canvas):
        self._app = canvas
        wc = self._wc = max(2, self.width // canvas.SCALE)
        hc = self._hc = max(3, self.height // canvas.SCALE)
        x, y = self.abs_x, self.abs_y
        focused = canvas.focused is self
        raw_bg = self.style.raw_bg

        for r in range(hc):  # clear the zone (paints the bg)
            canvas.write(x, y + r, " " * wc, self.style)

        # dashed border — accented + bold when focused ("ready to receive")
        bs = (
            Style(fg=self.accent, bg=raw_bg, styles=["bold"])
            if focused
            else Style(fg="bright_black", bg=raw_bg)
        )
        dash = "┄" * (wc - 2)
        canvas.write(x, y, "╭" + dash + "╮", bs)
        canvas.write(x, y + hc - 1, "╰" + dash + "╯", bs)
        for r in range(1, hc - 1):
            canvas.write(x, y + r, "┆", bs)
            canvas.write(x + wc - 1, y + r, "┆", bs)

        # centered content: icon, then the hint (or the path being entered),
        # a secondary line, and a status line
        cy = hc // 2
        icon_style = (
            Style(fg=self.accent, bg=raw_bg)
            if focused
            else Style(fg="bright_black", bg=raw_bg)
        )
        self._center(canvas, cy - 1, "⬇", icon_style)

        if focused and self._pending:
            # a raw-typed / hand-entered path, tail-clipped so the name stays visible
            self._center(
                canvas,
                cy,
                tail_clip_text(self._pending, wc - 2),
                Style(fg="bright_white", bg=raw_bg, styles=["bold"]),
            )
            self._center(
                canvas, cy + 1, "⏎ Enter to file it", Style(fg=self.accent, bg=raw_bg)
            )
        else:
            self._center(
                canvas, cy, self.hint, Style(fg="white", bg=raw_bg, styles=["bold"])
            )
            if not focused:
                sub, sub_style = "(click / Tab to focus)", Style(
                    fg="bright_black", bg=raw_bg
                )
            elif self._recent:
                sub, sub_style = "✓ " + ", ".join(self._recent), Style(
                    fg="bright_green", bg=raw_bg
                )
            elif self.accept:
                sub, sub_style = "Accepts: " + ", ".join(self.accept), Style(
                    fg="bright_black", bg=raw_bg
                )
            else:
                sub, sub_style = "or paste / type a path + ⏎", Style(
                    fg="bright_black", bg=raw_bg
                )
            self._center(canvas, cy + 1, sub, sub_style)

        if self._status:
            st = (
                Style(fg="bright_yellow", bg=raw_bg)
                if self._error
                else Style(fg="bright_green", bg=raw_bg)
            )
            self._center(canvas, hc - 2, self._status, st)
