"""Image widget: quadrant-block rendering, its cache, the Pillow-esque
fluent builder API (load_img/resize/crop/blur/save/render), and the
lazy-Pillow import guard used when Pillow isn't installed."""

import pytest

pytest.importorskip("PIL")  # self-skip this whole module without Pillow, like
# tests/test_clipboard.py self-skips without a platform clipboard backend.

from PIL import Image as PILImage

from cozy_tui import App, Style
from cozy_tui.widgets import Image
from cozy_tui.widgets.display.image import _DEFAULT_COLS, _ensure_pillow


def make_app():
    return App(full=False, size="800x400", style=Style(fg="white", bg="black"))


def make_gradient(tmp_path, name="g.png", w=20, h=10):
    path = tmp_path / name
    img = PILImage.new("RGB", (w, h))
    for x in range(w):
        for y in range(h):
            img.putpixel((x, y), (x * 10 % 256, y * 20 % 256, 128))
    img.save(path)
    return str(path)


@pytest.fixture
def missing_pillow(monkeypatch):
    """Simulate Pillow not being installed for the duration of a test --
    `import PIL` (and anything under it) raises ImportError."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "PIL" or name.startswith("PIL."):
            raise ImportError("simulated: no module named PIL")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)


def test_image_constructor_loads_source_and_positions(tmp_path):
    app = make_app()
    path = make_gradient(tmp_path)
    img = Image(3, 4, path)
    assert img.x == 3 and img.y == 4
    assert img._pil_image is not None
    app.add(img)
    app.snapshot()
    assert img._cache is not None


def test_default_size_auto_fits_aspect_ratio(tmp_path):
    # 20x10 source (2:1 w:h) at the default col width -> rows ~= cols *
    # h/w * cell_aspect(0.5) -- the 0.5 keeps a square/wide source from
    # rendering into a tall, visibly stretched box, since terminal cells
    # are ~2x taller than wide.
    path = make_gradient(tmp_path, w=20, h=10)
    img = Image(0, 0, path)
    assert img.natural_width(10) == _DEFAULT_COLS
    assert img.natural_height(10) == round(_DEFAULT_COLS * 10 / 20 * 0.5)


def test_explicit_size_overrides_auto_fit(tmp_path):
    path = make_gradient(tmp_path)
    img = Image(0, 0, path, size="100x60")
    assert img.natural_width(10) == 10
    assert img.natural_height(10) == 6


def test_draw_builds_a_cache_of_the_right_shape(tmp_path):
    app = make_app()
    img = Image(0, 0, make_gradient(tmp_path), size="80x40")
    app.add(img)
    app.snapshot()
    assert img._cache_size == (8, 4)
    assert len(img._cache) == 4
    assert all(len(row) == 8 for row in img._cache)
    assert all(
        isinstance(glyph, str) and isinstance(style, Style)
        for row in img._cache
        for glyph, style in row
    )


def test_cache_is_not_rebuilt_on_an_unchanged_redraw(tmp_path):
    app = make_app()
    img = Image(0, 0, make_gradient(tmp_path), size="40x20")
    app.add(img)
    app.snapshot()
    cache_before = img._cache
    app.snapshot()
    app.snapshot()
    assert img._cache is cache_before  # same object -- never rebuilt


def test_resize_invalidates_the_cache(tmp_path):
    app = make_app()
    img = Image(0, 0, make_gradient(tmp_path), size="40x20")
    app.add(img)
    app.snapshot()
    assert img._cache_size == (4, 2)
    img.resize("80x40")
    app.snapshot()
    assert img._cache_size == (8, 4)


def test_crop_trims_the_expected_box_and_invalidates(tmp_path):
    img = Image(0, 0, make_gradient(tmp_path, w=20, h=10))
    img.crop(top=1, left=2, bottom=3, right=4)
    assert img._pil_image.size == (20 - 2 - 4, 10 - 1 - 3)
    assert img._dirty is True


def test_blur_invalidates_the_cache(tmp_path):
    app = make_app()
    img = Image(0, 0, make_gradient(tmp_path), size="40x20")
    app.add(img)
    app.snapshot()
    img.blur(3)
    assert img._dirty is True
    app.snapshot()
    assert img._dirty is False  # rebuilt on the next draw


def test_save_writes_the_current_pixels(tmp_path):
    img = Image(0, 0, make_gradient(tmp_path))
    img.crop(top=1, left=1)
    out = tmp_path / "out.png"
    result = img.save(str(out))
    assert result is img
    assert out.exists()
    saved = PILImage.open(out)
    assert saved.size == img._pil_image.size


def test_render_repositions_and_returns_self():
    img = Image()
    result = img.render(7, 9)
    assert result is img
    assert img.x == 7 and img.y == 9


def test_fluent_chain_matches_the_pillow_esque_sketch(tmp_path):
    app = make_app()
    path = make_gradient(tmp_path)
    img = Image().load_img(path).resize("40x20").render(2, 2)
    app.add(img)
    app.snapshot()
    assert img.x == 2 and img.y == 2
    assert img._cache_size == (4, 2)


def test_mutators_all_return_self_for_chaining(tmp_path):
    img = Image(0, 0, make_gradient(tmp_path, "a.png"))
    assert img.load_img(make_gradient(tmp_path, "b.png")) is img
    assert img.resize("40x20") is img
    assert img.crop(top=1) is img
    assert img.blur(1) is img


def test_reload_rereads_the_same_source(tmp_path):
    path = make_gradient(tmp_path)
    img = Image(0, 0, path)
    img.crop(top=1, left=1)
    cropped_size = img._pil_image.size
    img.reload()
    assert img._pil_image.size != cropped_size  # back to the original, uncropped


def test_rebuild_cache_uses_lanczos_resampling(tmp_path, monkeypatch):
    calls = []
    original_resize = PILImage.Image.resize

    def spy_resize(self, size, resample=None, *a, **k):
        calls.append(resample)
        return original_resize(self, size, resample=resample, *a, **k)

    monkeypatch.setattr(PILImage.Image, "resize", spy_resize)

    app = make_app()
    img = Image(0, 0, make_gradient(tmp_path), size="40x20")
    app.add(img)
    app.snapshot()
    assert calls == [PILImage.Resampling.LANCZOS]


# ── load_img_async: background-thread loading via App.run_worker ────────────


def test_load_img_async_returns_self_immediately(tmp_path):
    app = make_app()
    img = Image()
    result = img.load_img_async(make_gradient(tmp_path), app)
    assert result is img


def test_load_img_async_loads_and_calls_on_ready(tmp_path):
    app = make_app()
    path = make_gradient(tmp_path)
    img = Image()
    ready = []
    img.load_img_async(path, app, on_ready=ready.append)
    img._async_load_thread.join(timeout=2)
    assert app._drain_workers() is True
    assert img._pil_image is not None
    assert ready == [img]


def test_load_img_async_missing_pillow_shows_placeholder(missing_pillow, tmp_path):
    app = make_app()
    img = Image()
    img.load_img_async(str(tmp_path / "cat.jpg"), app)  # path need not even exist
    img._async_load_thread.join(timeout=2)
    app._drain_workers()
    assert img._pil_image is None
    assert img._missing_pillow_message is not None


def test_load_img_async_bad_path_calls_on_error(tmp_path):
    app = make_app()
    img = Image()
    errors = []
    img.load_img_async(
        str(tmp_path / "does_not_exist.png"), app, on_error=errors.append
    )
    img._async_load_thread.join(timeout=2)
    app._drain_workers()
    assert len(errors) == 1
    assert isinstance(errors[0], FileNotFoundError)


def test_load_img_async_bad_path_toasts_when_no_on_error_given(tmp_path):
    app = make_app()
    img = Image()
    img.load_img_async(str(tmp_path / "does_not_exist.png"), app)
    img._async_load_thread.join(timeout=2)
    app._drain_workers()
    assert any(t.level == "error" for t in app._toasts)


def test_quadrant_glyph_and_truecolor_styles(tmp_path):
    app = make_app()
    path = make_gradient(tmp_path)
    img = Image(0, 0, path, size="40x20")
    app.add(img)
    app.snapshot()
    cell = app.buffer[0][0]
    assert cell.char in " ▘▝▖▗▀▄▌▐▚▞▛▜▙▟█"
    assert cell.style.fg.startswith("rgb(")
    assert cell.style.bg.startswith("rgb(")


def test_quadrant_cell_picks_the_right_glyph_and_colors():
    from cozy_tui.widgets.display.image import _quadrant_cell

    # Top row bright, bottom row dark -> upper-half-block, fg=top, bg=bottom.
    glyph, fg, bg = _quadrant_cell(
        (255, 255, 255), (250, 250, 250), (0, 0, 0), (5, 5, 5)
    )
    assert glyph == "▀"
    assert fg == (252, 252, 252)
    assert bg == (2, 2, 2)

    # All four pixels identical -> full block, single color.
    glyph, fg, bg = _quadrant_cell(
        (10, 20, 30), (10, 20, 30), (10, 20, 30), (10, 20, 30)
    )
    assert glyph == "█"
    assert fg == bg == (10, 20, 30)


def test_image_is_importable_without_constructing_anything():
    # from cozy_tui.widgets import Image must always work regardless of
    # whether Pillow is installed -- only actually using it should require it.
    from cozy_tui.widgets import Image as ImportedImage

    assert ImportedImage is Image


def test_ensure_pillow_raises_a_clear_error_when_pillow_missing(missing_pillow):
    with pytest.raises(ImportError, match=r"cozy-tui\[image\]"):
        _ensure_pillow()


# ── graceful placeholder when Pillow isn't installed ─────────────────────────


def test_load_img_does_not_raise_when_pillow_missing(missing_pillow, tmp_path):
    img = Image(2, 1, str(tmp_path / "cat.jpg"))  # path need not even exist
    assert img._pil_image is None
    assert img._missing_pillow_message is not None
    assert "cozy-tui[image]" in img._missing_pillow_message


def test_placeholder_renders_a_bordered_warning_box(missing_pillow, tmp_path):
    app = make_app()
    img = Image(2, 1, str(tmp_path / "cat.jpg"))
    app.add(img)
    snap = app.snapshot()
    assert "Rendering images requires" in snap
    assert "cozy-tui[image]" in snap
    assert "┌" in snap and "┐" in snap and "└" in snap and "┘" in snap


def test_placeholder_box_borders_are_aligned(missing_pillow, tmp_path):
    # Regression: padding the wrapped text with str.ljust() (character-count
    # based) instead of display-width-based padding misaligned the right
    # border whenever the message contains a zero-width character (here,
    # the warning message's own "⚠️" variation selector) -- each interior
    # row must have exactly one border glyph at each edge, nothing extra.
    app = make_app()
    img = Image(2, 1, str(tmp_path / "cat.jpg"))
    app.add(img)
    app.snapshot()
    cols = img.natural_width(app.SCALE)
    for row_off in range(1, img.natural_height(app.SCALE) - 1):
        row = app.buffer[img.abs_y + row_off]
        assert row[img.abs_x].char == "│"
        assert row[img.abs_x + cols - 1].char == "│"
        assert row[img.abs_x + cols].char != "│"  # nothing bleeds past the box


def test_placeholder_natural_size_has_a_sane_fallback(missing_pillow, tmp_path):
    img = Image(2, 1, str(tmp_path / "cat.jpg"))
    assert img.natural_width(10) > 0
    assert img.natural_height(10) >= 3  # at least top border + text + bottom border


def test_crop_and_blur_are_safe_noops_without_pillow(missing_pillow, tmp_path):
    img = Image(2, 1, str(tmp_path / "cat.jpg"))
    result = img.crop(top=1).blur(2)  # must not raise
    assert result is img
    assert img._pil_image is None


def test_save_raises_a_clear_error_without_a_loaded_image(missing_pillow, tmp_path):
    img = Image(2, 1, str(tmp_path / "cat.jpg"))
    with pytest.raises(RuntimeError):
        img.save(str(tmp_path / "out.png"))


def test_explicit_size_is_honored_even_for_the_placeholder(missing_pillow, tmp_path):
    img = Image(2, 1, str(tmp_path / "cat.jpg"), size="400x100")
    assert img.natural_width(10) == 40
    assert img.natural_height(10) == 10
