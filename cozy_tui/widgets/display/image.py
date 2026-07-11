import os

from cozy_tui._width import clip_text, text_width
from cozy_tui.style import Style
from cozy_tui.widget import Widget

_DEFAULT_COLS = 100
_PLACEHOLDER_COLS = 34  # width of the "Pillow missing" box when no size is set

# Typical monospace cell width:height ratio (cells are ~2x taller than wide) --
# used to keep an auto-fit image undistorted: without this, a square source
# image would render into a visibly tall/stretched box.
_CELL_ASPECT = 0.5

# 2x2-subpixel "quadrant" block rendering: each cell packs FOUR source pixels
# (not just two, like a plain upper-half-block) by picking two representative
# colors (fg/bg) and the one of these 16 Block Elements glyphs whose "on"
# pattern best matches which quadrants are closer to which color. All in the
# same widely-supported Unicode range as "▀" (U+2580-259F) -- no reliance on
# newer/rarer "Legacy Computing" sextant/octant glyphs.
# Bit order: 8=upper-left, 4=upper-right, 2=lower-left, 1=lower-right.
_QUADRANT_GLYPHS = {
    0b0000: " ",
    0b1000: "▘",
    0b0100: "▝",
    0b0010: "▖",
    0b0001: "▗",
    0b1100: "▀",
    0b0011: "▄",
    0b1010: "▌",
    0b0101: "▐",
    0b1001: "▚",
    0b0110: "▞",
    0b1110: "▛",
    0b1101: "▜",
    0b1011: "▙",
    0b0111: "▟",
    0b1111: "█",
}

_MISSING_PILLOW_MSG = (
    "⚠️ Rendering images requires Pillow installed. Try pip install "
    "cozy-tui[image] for the image to render."
)


def _ensure_pillow():
    try:
        from PIL import Image as PILImage
    except ImportError as exc:
        raise ImportError(
            "The Image widget needs Pillow -- install it with "
            "`pip install cozy-tui[image]`"
        ) from exc
    return PILImage


def _luminance(p: tuple[int, int, int]) -> float:
    r, g, b = p
    return 0.299 * r + 0.587 * g + 0.114 * b


def _avg_color(pixels: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    n = len(pixels)
    return (
        sum(p[0] for p in pixels) // n,
        sum(p[1] for p in pixels) // n,
        sum(p[2] for p in pixels) // n,
    )


def _quadrant_cell(ul, ur, ll, lr) -> tuple[str, tuple, tuple]:
    """Classify one 2x2 block of source pixels into (glyph, fg_rgb, bg_rgb):
    split the four into "bright"/"dark" halves by luminance vs. their own
    mean, average each half into one representative color, and pick the
    glyph whose quadrant pattern matches the bright half."""
    pixels = (ul, ur, ll, lr)
    lums = [_luminance(p) for p in pixels]
    mean_lum = sum(lums) / 4
    mask = 0
    bright, dark = [], []
    for bit, p, lum in zip((8, 4, 2, 1), pixels, lums):
        if lum >= mean_lum:
            mask |= bit
            bright.append(p)
        else:
            dark.append(p)
    fg = _avg_color(bright) if bright else (0, 0, 0)
    bg = _avg_color(dark) if dark else fg
    return _QUADRANT_GLYPHS[mask], fg, bg


def _wrap_text(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and text_width(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


class Image(Widget):
    """A raster image rendered in the terminal via 2x2 "quadrant" truecolor
    blocks: each cell packs *four* source pixels, split into two
    representative colors (fg/bg) and drawn with whichever of the 16 Unicode
    Block Elements glyphs (``▘▝▖▗▀▄▌▐▚▞▛▜▙▟█``, all in the same widely
    supported range as the simpler upper-half-block) best matches which
    quadrants are closer to which color -- double the effective resolution
    of plain half-block rendering, in both directions. Requires Pillow
    (``pip install cozy-tui[image]``) -- lazily imported, so ``from
    cozy_tui.widgets import Image`` always works even without it installed;
    only actually loading an image raises, with an install hint.

    Two ways to build one:

    * ``Image(x, y, "cat.png")`` -- position + source up front.
    * ``Image().load_img("cat.png").resize("400x300").render(x, y)`` -- a
      Pillow-esque fluent builder; every mutator returns ``self``.

    ``load_img_async(source, app)`` loads on a background thread instead
    (via ``App.run_worker``), for a large image or a slow disk read that
    shouldn't stall the render loop while it decodes.

    The Pillow work (resize + pixel sampling) only happens once per distinct
    (source, target cell size) -- see ``draw()`` -- not on every frame, so
    holding an Image on screen costs no more than blitting prebuilt styles.
    """

    def __init__(self, x=0, y=0, source=None, *, size=None, style=None):
        super().__init__(x, y, style, name="Image")
        self._pil_image = None
        self._source = None
        self._target_w_px: int | None = None
        self._target_h_px: int | None = None
        self._cache: list[list[tuple[str, Style]]] | None = None
        self._cache_size: tuple[int, int] | None = None
        self._dirty = False
        self._missing_pillow_message: str | None = None
        self._async_load_thread = None
        if source is not None:
            self.load_img(source)
        if size is not None:
            self.resize(size)

    # ── Pillow-esque builder API ─────────────────────────────────────────────

    def load_img(self, source) -> "Image":
        """Load (or replace) the source image from a file path. Returns
        ``self`` for chaining. If Pillow itself isn't installed, this does
        *not* raise -- ``draw()`` instead renders a bordered placeholder
        explaining how to install it (``pip install cozy-tui[image]``), so a
        missing optional dependency degrades gracefully instead of crashing
        the whole app. A bad/corrupt `source` still raises normally, same as
        Pillow's own `Image.open` -- that's a real bug to fix, not an
        environment gap to paper over."""
        self._source = source
        try:
            PILImage = _ensure_pillow()
        except ImportError:
            self._pil_image = None
            self._missing_pillow_message = _MISSING_PILLOW_MSG
            self._dirty = True
            return self
        self._pil_image = PILImage.open(source).convert("RGB")
        self._missing_pillow_message = None
        self._dirty = True
        return self

    def load_img_async(self, source, app, *, on_ready=None, on_error=None) -> "Image":
        """Load `source` on a background thread (via `App.run_worker`) so a
        large image or a slow disk read doesn't block the render loop while
        it decodes. Returns `self` immediately -- nothing is loaded yet.
        Needs `app` (the `App` this widget is/will be added to) since a
        widget has no back-reference to its own app; the result is
        delivered back and applied on the **main thread**, followed by
        `run_worker`'s own re-render.

        A missing Pillow install still degrades to the same warning
        placeholder `load_img` shows. Any other failure (bad path, corrupt
        file) calls `on_error(exc)` if given, else shows an error toast --
        there's no caller left to raise back to once loading has moved to a
        background thread."""
        self._source = source

        def _load():
            PILImage = _ensure_pillow()
            return PILImage.open(source).convert("RGB")

        def _on_result(pil_image) -> None:
            self._pil_image = pil_image
            self._missing_pillow_message = None
            self._dirty = True
            if on_ready is not None:
                on_ready(self)

        def _on_error(exc) -> None:
            if isinstance(exc, ImportError):
                self._pil_image = None
                self._missing_pillow_message = _MISSING_PILLOW_MSG
                self._dirty = True
                if on_ready is not None:
                    on_ready(self)
                return
            if on_error is not None:
                on_error(exc)
            else:
                app.toast(f"Image failed to load: {exc}", level="error")

        # Stashed (not just fire-and-forget) so a caller -- or a test -- can
        # `.join()` it to wait for the load deterministically.
        self._async_load_thread = app.run_worker(
            _load, on_result=_on_result, on_error=_on_error
        )
        return self

    def reload(self) -> "Image":
        """Re-read the current source file from disk (e.g. it changed on
        disk) and invalidate the cache."""
        if self._source is not None:
            self.load_img(self._source)
        return self

    def resize(self, size: str) -> "Image":
        """Set the target *cell* size as a ``"WIDTHxHEIGHT"`` virtual-pixel
        string (÷ ``App.SCALE`` for cells) -- the same convention
        ``Box``/``ScrollView``/``Splitter`` use. This does not touch the
        source image's own pixels, only how many cells it's sampled down to;
        see ``crop``/``blur`` to change the source itself."""
        w, h = size.split("x")
        self._target_w_px, self._target_h_px = int(w), int(h)
        return self

    def crop(self, *, top=0, left=0, bottom=0, right=0) -> "Image":
        """Trim pixels off the given edges of the source image (unlike
        Pillow's own absolute box coordinates). Returns ``self``. A no-op
        while there's no loaded image (e.g. Pillow is missing), so a fluent
        chain stays safe end to end."""
        if self._pil_image is None:
            return self
        w, h = self._pil_image.size
        self._pil_image = self._pil_image.crop((left, top, w - right, h - bottom))
        self._dirty = True
        return self

    def blur(self, radius: float = 2) -> "Image":
        """Gaussian-blur the source image (``PIL.ImageFilter.GaussianBlur``).
        Returns ``self``. A no-op while there's no loaded image (e.g. Pillow
        is missing)."""
        if self._pil_image is None:
            return self
        from PIL import ImageFilter

        self._pil_image = self._pil_image.filter(ImageFilter.GaussianBlur(radius))
        self._dirty = True
        return self

    def save(self, path) -> "Image":
        """Save the current (possibly cropped/resized/blurred) image to
        disk. Returns ``self``. Raises if there's no loaded image to save
        (e.g. Pillow is missing) -- unlike `crop`/`blur`, silently doing
        nothing here would hide a file that was never written."""
        if self._pil_image is None:
            raise RuntimeError(
                "Image.save(): no image loaded (Pillow missing or load failed)"
            )
        self._pil_image.save(os.path.expanduser(str(path)))
        return self

    def render(self, x, y) -> "Image":
        """Position this widget at ``(x, y)`` in parent-relative cells.
        Returns ``self`` so it chains straight into ``app.add(...)``. This
        only repositions -- actual drawing still happens through the normal
        ``draw()`` cycle once the widget is added to an ``App``."""
        self.x, self.y = x, y
        return self

    # ── sizing ────────────────────────────────────────────────────────────────

    def _cols(self, scale: int) -> int:
        if self._target_w_px is not None:
            return max(1, self._target_w_px // scale)
        if self._pil_image is None and self._missing_pillow_message is not None:
            return _PLACEHOLDER_COLS
        return _DEFAULT_COLS

    def _rows(self, scale: int) -> int:
        if self._target_h_px is not None:
            return max(1, self._target_h_px // scale)
        if self._pil_image is not None:
            w, h = self._pil_image.size
            return max(1, round(self._cols(scale) * h / w * _CELL_ASPECT))
        if self._missing_pillow_message is not None:
            lines = _wrap_text(self._missing_pillow_message, self._cols(scale) - 2)
            return len(lines) + 2  # + top/bottom border rows
        return 1

    def natural_width(self, scale) -> int:
        return self._cols(scale)

    def natural_height(self, scale) -> int:
        return self._rows(scale)

    # ── cache + draw ──────────────────────────────────────────────────────────

    def _rebuild_cache(self, cols: int, rows: int) -> None:
        from PIL import Image as PILImage

        # 2 source pixels per cell in EACH direction: quadrant rendering
        # samples a 2x2 block per cell, not just a top/bottom pair. LANCZOS
        # (a high-quality windowed-sinc filter) noticeably sharpens detail on
        # this kind of large downscale vs. Pillow's own resize() default.
        resized = self._pil_image.resize(
            (cols * 2, rows * 2), resample=PILImage.Resampling.LANCZOS
        )
        pixels = resized.load()
        cache = []
        for cy in range(rows):
            row_cells = []
            for cx in range(cols):
                x0, y0 = cx * 2, cy * 2
                glyph, fg, bg = _quadrant_cell(
                    pixels[x0, y0],
                    pixels[x0 + 1, y0],
                    pixels[x0, y0 + 1],
                    pixels[x0 + 1, y0 + 1],
                )
                style = Style(
                    fg=f"rgb({fg[0]},{fg[1]},{fg[2]})",
                    bg=f"rgb({bg[0]},{bg[1]},{bg[2]})",
                )
                row_cells.append((glyph, style))
            cache.append(row_cells)
        self._cache = cache
        self._cache_size = (cols, rows)
        self._dirty = False

    def _draw_missing_pillow(self, canvas) -> None:
        from cozy_tui.theme import get_theme  # local: theme.py builds on Style

        cols, rows = self._cols(canvas.SCALE), self._rows(canvas.SCALE)
        if cols < 4 or rows < 3:
            return
        warn = get_theme().warning
        raw_bg = self.style.raw_bg
        border = Style(fg=warn, bg=raw_bg, styles=["bold"])
        text_style = Style(fg=warn, bg=raw_bg)
        x, y, inner_w = self.abs_x, self.abs_y, cols - 2

        canvas.write(x, y, "┌" + "─" * inner_w + "┐", border)
        lines = _wrap_text(self._missing_pillow_message, inner_w)
        for i in range(rows - 2):
            text = clip_text(lines[i], inner_w) if i < len(lines) else ""
            padded = text + " " * max(0, inner_w - text_width(text))
            canvas.write(x, y + 1 + i, "│" + padded + "│", text_style)
            canvas.write(x, y + 1 + i, "│", border)
            canvas.write(x + cols - 1, y + 1 + i, "│", border)
        canvas.write(x, y + rows - 1, "└" + "─" * inner_w + "┘", border)

    def draw(self, canvas) -> None:
        if self._missing_pillow_message is not None:
            self._draw_missing_pillow(canvas)
            return
        if self._pil_image is None:
            return
        cols, rows = self._cols(canvas.SCALE), self._rows(canvas.SCALE)
        if cols <= 0 or rows <= 0:
            return
        if self._dirty or self._cache_size != (cols, rows):
            self._rebuild_cache(cols, rows)
        for cy, row_cells in enumerate(self._cache):
            for cx, (glyph, style) in enumerate(row_cells):
                canvas.write(self.abs_x + cx, self.abs_y + cy, glyph, style)
