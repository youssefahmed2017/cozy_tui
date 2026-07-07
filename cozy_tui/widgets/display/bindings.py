from cozy_tui._width import text_width
from cozy_tui.events import Key
from cozy_tui.style import Style
from cozy_tui.widget import Widget
from cozy_tui.widgets.layout.box import Box


class Bindings(Widget):
    """A self-sizing key-bindings legend.

    ``bindings`` may be:

    * a flat ``{key: description}`` dict::

          Bindings(60, 2, {"↑": "Move Up", "Esc": "Quit"}, title="Keys")

    * a grouped ``{section: {key: description}}`` dict (sections get headers), or

    * ``"auto"`` / an ``App`` — pull the app's registered bindings live::

          app.on_key(Key.ESC, app.quit, description="Quit", section="Actions")
          app.add(Bindings(60, 2, "auto"))     # or Bindings(60, 2, app)

      Only bindings registered *with a description* are shown; keys are rendered
      via ``Key.label`` (e.g. ``Key.ESC`` → ``Esc``). The legend re-syncs
      automatically whenever the app's bindings change.

    The widget draws its own auto-sized bordered panel — you never give it a
    width or height.
    """

    _GAP = 3  # spaces between the key column and the description

    def __init__(self, x, y, bindings, *, title=None, border="rounded", style=None):
        super().__init__(x, y, style, name="Bindings")
        if border not in Box.BORDERS:
            raise ValueError(
                f"border must be one of {list(Box.BORDERS)}, got {border!r}"
            )
        self.title = title
        self.border = border

        raw_bg = self.style.raw_bg
        self._border_style = Style(fg="bright_black", bg=raw_bg)
        self._key_style = Style(fg="bright_cyan", bg=raw_bg, styles=["bold"])
        self._header_style = Style(fg="bright_yellow", bg=raw_bg, styles=["bold"])
        self._desc_style = Style(fg=self.style.fg or "white", bg=raw_bg)

        # Resolve the source mode.
        self._app = None
        self._synced_version = None
        self._rows, self._key_w, self._content_w = [], 0, 0
        if isinstance(bindings, str):
            if bindings != "auto":
                raise ValueError('string bindings must be "auto"')
            self._mode = "canvas"  # app comes from the draw canvas
        elif isinstance(bindings, dict):
            self._mode = "static"
            self._build(bindings)
        elif hasattr(bindings, "_bindings") and hasattr(bindings, "_bindings_version"):
            self._mode = "app"
            self._app = bindings
            self._sync(bindings)
        else:
            raise TypeError('bindings must be a dict, an App, or "auto"')

    # ── syncing from an app ────────────────────────────────────────────────────

    def _sync(self, app) -> None:
        if app is None:
            return
        version = getattr(app, "_bindings_version", None)
        if version is None or version == self._synced_version:
            return
        self._build(self._source_from_app(app))
        self._synced_version = version

    @staticmethod
    def _source_from_app(app):
        """Turn app._bindings ({key: (desc, section)}) into a flat or sectioned
        source dict, relabeling keys and preserving registration order."""
        groups: dict = {}
        ungrouped: dict = {}
        for key, (desc, section) in app._bindings.items():
            label = Key.label(key)
            (ungrouped if section is None else groups.setdefault(section, {}))[
                label
            ] = desc
        if not groups:
            return ungrouped
        source = {}
        if ungrouped:
            source["General"] = ungrouped
        source.update(groups)  # sections in first-appearance order
        return source

    # ── measurement ────────────────────────────────────────────────────────────

    def _build(self, source):
        values = list(source.values())
        sectioned = bool(values) and all(isinstance(v, dict) for v in values)

        rows, keys, descs, headers = [], [], [], []
        if sectioned:
            for i, (name, section) in enumerate(source.items()):
                if i:
                    rows.append(("blank",))
                rows.append(("header", str(name)))
                headers.append(str(name))
                for key, desc in section.items():
                    rows.append(("bind", str(key), str(desc)))
                    keys.append(str(key))
                    descs.append(str(desc))
        else:
            for key, desc in source.items():
                rows.append(("bind", str(key), str(desc)))
                keys.append(str(key))
                descs.append(str(desc))

        self._rows = rows
        self._key_w = max((text_width(k) for k in keys), default=0)
        desc_w = max((text_width(d) for d in descs), default=0)
        body_w = self._key_w + (self._GAP if desc_w else 0) + desc_w
        header_w = max((text_width(h) for h in headers), default=0)
        title_w = text_width(self.title) if self.title else 0
        self._content_w = max(body_w, header_w, title_w)

    def natural_width(self, scale) -> int:
        self._sync(self._app)
        return self._content_w + 4  # 2 border + 1 pad each side

    def natural_height(self, scale) -> int:
        self._sync(self._app)
        return len(self._rows) + 2  # + top/bottom border

    def contains(self, col: int, row: int) -> bool:
        return self.abs_x <= col < self.abs_x + self.natural_width(
            1
        ) and self.abs_y <= row < self.abs_y + self.natural_height(1)

    # ── rendering ──────────────────────────────────────────────────────────────

    def draw(self, canvas) -> None:
        if self._mode == "canvas":
            self._app = canvas
        self._sync(self._app)

        corners, h, v = Box.BORDERS[self.border]
        tl, tr, bl, br = corners
        x, y = self.abs_x, self.abs_y
        iw = self._content_w + 2  # interior width (content + 1 pad each side)
        bs = self._border_style

        if self.title:
            t = f" {self.title} "
            top = tl + t + h * max(0, iw - text_width(t)) + tr
        else:
            top = tl + h * iw + tr
        canvas.write(x, y, top, bs)

        for i, row in enumerate(self._rows):
            vy = y + 1 + i
            canvas.write(x, vy, v, bs)
            canvas.write(x + iw + 1, vy, v, bs)
            canvas.write(x + 1, vy, " " * iw, self._desc_style)  # clear interior
            cx = x + 2  # inside the left border + 1 pad
            if row[0] == "header":
                canvas.write(cx, vy, row[1], self._header_style)
            elif row[0] == "bind":
                _, key, desc = row
                canvas.write(cx, vy, key, self._key_style)
                if desc:
                    canvas.write(
                        cx + self._key_w + self._GAP, vy, desc, self._desc_style
                    )

        canvas.write(x, y + 1 + len(self._rows), bl + h * iw + br, bs)
