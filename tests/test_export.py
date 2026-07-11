"""SVG/HTML screen export (`App.export_svg`/`export_html`/`save_screenshot`)
and its default Ctrl+S binding."""

import xml.etree.ElementTree as ET

import pytest

from cozy_tui import App, Style
from cozy_tui.events import Key
from cozy_tui.widgets import Label


def make_app():
    return App(full=False, size="400x100", style=Style(fg="white", bg="black"))


def test_export_svg_contains_text_and_is_well_formed():
    app = make_app()
    app.add(Label(2, 1, "Hello, Cozy TUI!"))
    svg = app.export_svg()
    assert svg.startswith("<svg ")
    assert svg.rstrip().endswith("</svg>")
    assert "Hello, Cozy TUI!" in svg


def test_export_html_contains_text_and_is_well_formed():
    app = make_app()
    app.add(Label(2, 1, "Hello, Cozy TUI!"))
    html = app.export_html()
    assert html.startswith("<!doctype html>")
    assert html.rstrip().endswith("</html>")
    assert "Hello, Cozy TUI!" in html


def test_svg_and_html_escape_special_characters():
    app = make_app()
    app.add(Label(2, 1, "<a & b>"))
    svg = app.export_svg()
    html = app.export_html()
    assert "&lt;a &amp; b&gt;" in svg
    assert "&lt;a &amp; b&gt;" in html
    assert "<a & b>" not in svg
    assert "<a & b>" not in html


def test_bold_and_underline_styles_are_baked_in():
    app = make_app()
    app.add(Label(2, 1, "Bold text", Style(fg="white", styles=["bold"])))
    app.add(Label(2, 2, "Underlined", Style(fg="white", styles=["underline"])))
    svg = app.export_svg()
    html = app.export_html()
    assert 'font-weight="bold"' in svg
    assert 'text-decoration="underline"' in svg
    assert "font-weight:bold" in html
    assert "text-decoration:underline" in html


def test_export_svg_writes_to_path(tmp_path):
    app = make_app()
    app.add(Label(2, 1, "on disk"))
    path = tmp_path / "screen.svg"
    result = app.export_svg(str(path))
    assert path.read_text(encoding="utf-8") == result
    assert "on disk" in path.read_text(encoding="utf-8")


def test_export_html_writes_to_path(tmp_path):
    app = make_app()
    app.add(Label(2, 1, "on disk"))
    path = tmp_path / "screen.html"
    result = app.export_html(str(path))
    assert path.read_text(encoding="utf-8") == result


def test_save_screenshot_infers_format_from_extension(tmp_path):
    app = make_app()
    svg_path = str(tmp_path / "shot.svg")
    html_path = str(tmp_path / "shot.html")
    assert app.save_screenshot(svg_path) == svg_path
    assert app.save_screenshot(html_path) == html_path
    assert (tmp_path / "shot.svg").read_text(encoding="utf-8").startswith("<svg ")
    assert (
        (tmp_path / "shot.html")
        .read_text(encoding="utf-8")
        .startswith("<!doctype html>")
    )


def test_save_screenshot_default_path_is_timestamped_svg(tmp_path, monkeypatch):
    from pathlib import Path

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    app = make_app()
    path = app.save_screenshot()
    assert Path(path).name.startswith("cozy_tui_") and path.endswith(".svg")
    assert Path(path).parent == tmp_path / ".cozy_tui" / "screenshots"
    assert Path(path).exists()


def test_save_screenshot_rejects_unknown_format(tmp_path):
    app = make_app()
    with pytest.raises(ValueError):
        app.save_screenshot(str(tmp_path / "shot"), format="pdf")


def test_ctrl_s_is_bound_to_quick_screenshot():
    app = make_app()
    assert app._key_handlers[Key.CTRL_S] == app._quick_screenshot


def test_quick_screenshot_shows_a_success_toast(tmp_path, monkeypatch):
    from pathlib import Path

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    app = make_app()
    app._quick_screenshot()
    assert any("Saved" in t.message for t in app._toasts)


def test_quick_screenshot_toasts_an_error_instead_of_raising(monkeypatch):
    app = make_app()

    def boom(path=None, *, format=None, frame=None, standalone=False):
        raise OSError("disk full")

    monkeypatch.setattr(app, "save_screenshot", boom)
    app._quick_screenshot()  # must not raise
    assert any("failed" in t.message.lower() for t in app._toasts)


def test_save_screenshot_command_is_registered():
    app = make_app()
    assert "Save Screenshot" in app._commands


# ── frame= window chrome ──────────────────────────────────────────────────────


@pytest.mark.parametrize("frame", ["macos", "windows", "gnome"])
def test_svg_frame_is_well_formed_and_contains_chrome(frame):
    app = make_app()
    app.add(Label(2, 1, "Framed!"))
    svg = app.export_svg(frame=frame)
    ET.fromstring(svg)  # raises if malformed
    assert "Framed!" in svg
    assert "cozy-shadow" in svg  # drop shadow filter
    assert "cozy-clip" in svg  # rounded-corner clip path
    assert 'rx="' in svg  # rounded window rect


def test_svg_no_frame_is_unchanged_raw_grid():
    app = make_app()
    app.add(Label(2, 1, "Plain"))
    svg = app.export_svg()
    assert "cozy-shadow" not in svg
    assert svg.startswith("<svg ")  # no outer margin/window wrapping


def test_svg_frame_rejects_unknown_name():
    app = make_app()
    with pytest.raises(ValueError):
        app.export_svg(frame="bogus")


def test_macos_frame_has_three_dots_and_centered_title():
    app = make_app()
    svg = app.export_svg(title="My App", frame="macos")
    assert svg.count("<circle") == 3
    assert 'text-anchor="middle"' in svg
    assert "My App" in svg


def test_windows_frame_has_window_buttons():
    app = make_app()
    svg = app.export_svg(frame="windows")
    assert "–" in svg and "□" in svg and "×" in svg


def test_gnome_frame_has_single_close_button():
    app = make_app()
    svg = app.export_svg(frame="gnome")
    assert svg.count("<circle") == 1


@pytest.mark.parametrize("frame", ["macos", "windows", "gnome"])
def test_html_frame_wraps_terminal_in_a_chrome_div(frame):
    app = make_app()
    app.add(Label(2, 1, "Framed!"))
    html = app.export_html(frame=frame)
    assert "Framed!" in html
    assert "box-shadow" in html
    assert "border-radius" in html


def test_html_frame_rejects_unknown_name():
    app = make_app()
    with pytest.raises(ValueError):
        app.export_html(frame="bogus")


# ── standalone=True HTML page ─────────────────────────────────────────────────


def test_standalone_html_has_dark_centered_page():
    app = make_app()
    html = app.export_html(standalone=True)
    assert "#15151a" in html  # dark page background
    assert "justify-content:center" in html
    assert "max-width:96vw" in html  # responsive: scrolls, doesn't overflow


def test_standalone_without_frame_still_gets_a_soft_box():
    app = make_app()
    html = app.export_html(standalone=True)
    assert "box-shadow" in html
    assert "border-radius" in html


def test_standalone_with_frame_does_not_double_the_shell_box():
    app = make_app()
    html = app.export_html(frame="gnome", standalone=True)
    # exactly one box-shadow: the frame's own, not a second one from the shell
    assert html.count("box-shadow") == 1


def test_non_standalone_html_has_no_dark_shell():
    app = make_app()
    html = app.export_html()
    assert "#15151a" not in html


def test_save_screenshot_forwards_frame_and_standalone(tmp_path):
    app = make_app()
    svg_path = str(tmp_path / "shot.svg")
    html_path = str(tmp_path / "shot.html")
    app.save_screenshot(svg_path, frame="macos")
    app.save_screenshot(html_path, frame="macos", standalone=True)
    assert "cozy-shadow" in (tmp_path / "shot.svg").read_text(encoding="utf-8")
    html_content = (tmp_path / "shot.html").read_text(encoding="utf-8")
    assert "#15151a" in html_content and "box-shadow" in html_content


def test_quick_screenshot_uses_macos_frame_by_default(tmp_path, monkeypatch):
    from pathlib import Path

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    app = make_app()
    app._quick_screenshot()
    path = tmp_path / ".cozy_tui" / "screenshots"
    saved = next(path.glob("*.svg"))
    assert "cozy-shadow" in saved.read_text(encoding="utf-8")
