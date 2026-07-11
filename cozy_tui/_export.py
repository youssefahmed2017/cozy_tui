"""Standalone SVG/HTML export of the current screen -- a `snapshot()` with
the actual resolved colors/styles baked in, for embedding in docs, READMEs,
or issue reports. See `App.export_svg`/`export_html`/`save_screenshot`
(bound to Ctrl+S by default).

Colors are resolved via `cozy_tui.ansi.resolve_rgb`, the same lookup the
real terminal renderer uses to downgrade truecolor/256-color values -- so
named colors, "#rrggbb", "rgb(R,G,B)", and "color(N)" all just work here
too, with no separate color table to keep in sync.

`frame=` ("macos"/"windows"/"gnome") wraps the raw cell grid in a fake OS
window -- a titlebar (traffic-light dots / window buttons + title) plus
rounded corners and a drop shadow, so the export reads as a screenshot of a
real terminal instead of text floating in a corner. `standalone=True` (HTML
only) goes further: a dark, centered page around it, matching what a reader
actually sees when they open the file rather than embed it.
"""

from html import escape as _html_escape
from xml.sax.saxutils import escape as _xml_escape

from cozy_tui.ansi import resolve_rgb

# Metrics for a common monospace stack at a comfortable reading size --
# not measured per-font (this library has no font-metrics dependency), just
# a reasonable fixed grid that keeps the exported text aligned.
_CELL_W = 9.6
_CELL_H = 20
_FONT_SIZE = 15
_FONT_FAMILY = "'Cascadia Code', 'Fira Code', Consolas, 'Courier New', monospace"

_TITLEBAR_H = 34
_FRAME_MARGIN = 22  # breathing room around the window for the drop shadow

# Visual identity per `frame=`, shared by both the SVG and HTML renderers.
# "kind" picks which titlebar decoration (dots / window buttons / a single
# close button) each builder draws -- these are deliberately stylized, not
# pixel-accurate OS mockups.
_FRAMES = {
    "macos": {
        "kind": "dots",
        "titlebar_bg": "#e3e2e0",
        "title_color": "#4b4b4b",
        "border": "#c7c6c4",
        "radius": 10,
    },
    "windows": {
        "kind": "win-buttons",
        "titlebar_bg": "#f3f3f3",
        "title_color": "#202020",
        "border": "#d1d1d1",
        "radius": 8,
    },
    "gnome": {
        "kind": "gnome-button",
        "titlebar_bg": "#2d2d2d",
        "title_color": "#e8e8e8",
        "border": "#1a1a1a",
        "radius": 12,
    },
}


def _validate_frame(frame) -> None:
    if frame is not None and frame not in _FRAMES:
        raise ValueError(
            f"frame must be one of {tuple(_FRAMES)} or None, got {frame!r}"
        )


def _rgb_hex(color, fallback: str) -> str:
    rgb = resolve_rgb(color)
    if rgb is None:
        return fallback
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _base_colors(app) -> tuple[str, str]:
    return (
        _rgb_hex(app.style.fg, "#e0e0e0"),
        _rgb_hex(app.style.raw_bg, "#000000"),
    )


def _cell_look(cell, base_fg: str, base_bg: str):
    style = cell.style
    return (
        _rgb_hex(style.fg, base_fg),
        _rgb_hex(style.raw_bg, base_bg),
        style.styles,
    )


def _iter_runs(app, base_fg: str, base_bg: str):
    """Yield (row, col_start, text, (fg_hex, bg_hex, styles)) -- each run is a
    maximal stretch of one row's cells sharing an identical look, so a mostly
    uniform screen produces a handful of runs instead of one element per cell."""
    for y, row in enumerate(app.buffer):
        if not row:
            continue
        run_start = 0
        run_look = _cell_look(row[0], base_fg, base_bg)
        run_text = []
        for x, cell in enumerate(row):
            look = _cell_look(cell, base_fg, base_bg)
            if look != run_look:
                if run_text:
                    yield y, run_start, "".join(run_text), run_look
                run_start = x
                run_look = look
                run_text = []
            run_text.append(cell.char)
        if run_text:
            yield y, run_start, "".join(run_text), run_look


# ── SVG ───────────────────────────────────────────────────────────────────────


def _content_svg_parts(
    app, base_fg: str, base_bg: str, content_w: float, content_h: float
):
    parts = [
        f'<rect width="{content_w:.1f}" height="{content_h:.1f}" fill="{base_bg}"/>'
    ]
    for y, x, text, (fg, bg, styles) in _iter_runs(app, base_fg, base_bg):
        rx = x * _CELL_W
        ry = y * _CELL_H
        run_w = len(text) * _CELL_W
        if bg != base_bg:
            parts.append(
                f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{run_w:.1f}" '
                f'height="{_CELL_H}" fill="{bg}"/>'
            )
        attrs = []
        if "bold" in styles:
            attrs.append('font-weight="bold"')
        if "italic" in styles:
            attrs.append('font-style="italic"')
        if "underline" in styles:
            attrs.append('text-decoration="underline"')
        if "dim" in styles:
            attrs.append('fill-opacity="0.6"')
        attr_str = (" " + " ".join(attrs)) if attrs else ""
        parts.append(
            f'<text x="{rx:.1f}" y="{ry + _CELL_H * 0.8:.1f}" fill="{fg}" '
            f'textLength="{run_w:.1f}" lengthAdjust="spacingAndGlyphs" '
            f'xml:space="preserve"{attr_str}>{_xml_escape(text)}</text>'
        )
    return parts


def _titlebar_svg_decor(spec, title: str, wx: float, wy: float, w: float) -> str:
    cy = wy + _TITLEBAR_H / 2
    parts = []
    kind = spec["kind"]

    if kind == "dots":
        for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
            cx = wx + 20 + i * 20
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="{c}"/>')
        text_x, anchor = wx + w / 2, "middle"
    elif kind == "win-buttons":
        for i, ch in enumerate(("–", "□", "×")):
            bx = wx + w - 18 - (2 - i) * 34
            parts.append(
                f'<text x="{bx:.1f}" y="{cy + 5:.1f}" fill="{spec["title_color"]}" '
                f'font-size="14" text-anchor="middle" '
                f'font-family="{_FONT_FAMILY}">{ch}</text>'
            )
        text_x, anchor = wx + 20, "start"
    else:  # gnome-button
        bx = wx + w - 24
        parts.append(f'<circle cx="{bx:.1f}" cy="{cy:.1f}" r="9" fill="#484848"/>')
        parts.append(
            f'<text x="{bx:.1f}" y="{cy + 4:.1f}" fill="{spec["title_color"]}" '
            f'font-size="12" text-anchor="middle" '
            f'font-family="{_FONT_FAMILY}">×</text>'
        )
        text_x, anchor = wx + w / 2, "middle"

    parts.append(
        f'<text x="{text_x:.1f}" y="{cy + 4.5:.1f}" fill="{spec["title_color"]}" '
        f'font-size="13" font-weight="600" text-anchor="{anchor}" '
        f'font-family="{_FONT_FAMILY}">{_xml_escape(title)}</text>'
    )
    return "\n".join(parts)


def _wrap_svg_frame(
    frame: str, title: str, content_w: float, content_h: float, content_parts
) -> str:
    spec = _FRAMES[frame]
    window_w, window_h = content_w, content_h + _TITLEBAR_H
    wx = wy = float(_FRAME_MARGIN)
    svg_w, svg_h = window_w + 2 * _FRAME_MARGIN, window_h + 2 * _FRAME_MARGIN
    radius = spec["radius"]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w:.1f}" '
        f'height="{svg_h:.1f}" font-family="{_FONT_FAMILY}" font-size="{_FONT_SIZE}">',
        f"<title>{_xml_escape(title)}</title>",
        "<defs>",
        '<filter id="cozy-shadow" x="-50%" y="-50%" width="200%" height="200%">',
        '<feDropShadow dx="0" dy="6" stdDeviation="10" '
        'flood-color="#000000" flood-opacity="0.35"/>',
        "</filter>",
        f'<clipPath id="cozy-clip"><rect x="{wx:.1f}" y="{wy:.1f}" '
        f'width="{window_w:.1f}" height="{window_h:.1f}" rx="{radius}"/></clipPath>',
        "</defs>",
        f'<rect x="{wx:.1f}" y="{wy:.1f}" width="{window_w:.1f}" height="{window_h:.1f}" '
        f'rx="{radius}" fill="{spec["titlebar_bg"]}" filter="url(#cozy-shadow)"/>',
        '<g clip-path="url(#cozy-clip)">',
        f'<rect x="{wx:.1f}" y="{wy:.1f}" width="{window_w:.1f}" height="{_TITLEBAR_H}" '
        f'fill="{spec["titlebar_bg"]}"/>',
        _titlebar_svg_decor(spec, title, wx, wy, window_w),
        f'<g transform="translate({wx:.1f},{wy + _TITLEBAR_H:.1f})">',
        *content_parts,
        "</g>",
        "</g>",
        f'<rect x="{wx:.1f}" y="{wy:.1f}" width="{window_w:.1f}" height="{window_h:.1f}" '
        f'rx="{radius}" fill="none" stroke="{spec["border"]}" stroke-width="1"/>',
        "</svg>",
    ]
    return "\n".join(parts) + "\n"


def render_svg(app, *, title: str | None = None, frame: str | None = None) -> str:
    """Render `app`'s current screen (call `App._compose()` first, as the
    export methods on `App` do) as a standalone SVG document. `frame`
    ("macos"/"windows"/"gnome") wraps it in a fake OS window with a
    titlebar, rounded corners, and a drop shadow."""
    _validate_frame(frame)
    base_fg, base_bg = _base_colors(app)
    content_w = app.cols * _CELL_W
    content_h = app.rows * _CELL_H
    title = title or app.title or "Cozy TUI"
    content_parts = _content_svg_parts(app, base_fg, base_bg, content_w, content_h)

    if frame is not None:
        return _wrap_svg_frame(frame, title, content_w, content_h, content_parts)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{content_w:.1f}" '
        f'height="{content_h:.1f}" font-family="{_FONT_FAMILY}" '
        f'font-size="{_FONT_SIZE}">',
        f"<title>{_xml_escape(title)}</title>",
        *content_parts,
        "</svg>",
    ]
    return "\n".join(parts) + "\n"


# ── HTML ──────────────────────────────────────────────────────────────────────


def _content_html_body(app, base_fg: str, base_bg: str) -> str:
    rows_html: list[list[str]] = [[] for _ in range(app.rows)]
    for y, x, text, (fg, bg, styles) in _iter_runs(app, base_fg, base_bg):
        css = [f"color:{fg}"]
        if bg != base_bg:
            css.append(f"background:{bg}")
        if "bold" in styles:
            css.append("font-weight:bold")
        if "italic" in styles:
            css.append("font-style:italic")
        if "underline" in styles:
            css.append("text-decoration:underline")
        if "dim" in styles:
            css.append("opacity:0.6")
        rows_html[y].append(
            f'<span style="{";".join(css)}">{_html_escape(text)}</span>'
        )
    return "\n".join("".join(spans) for spans in rows_html)


def _titlebar_html(spec, title: str) -> str:
    kind = spec["kind"]
    if kind == "dots":
        left = (
            '<span style="display:inline-flex;gap:8px;">'
            + "".join(
                f'<span style="width:12px;height:12px;border-radius:50%;'
                f'background:{c};display:inline-block;"></span>'
                for c in ("#ff5f56", "#ffbd2e", "#27c93f")
            )
            + "</span>"
        )
        right = ""
    elif kind == "win-buttons":
        left = ""
        right = (
            f'<span style="display:inline-flex;gap:18px;font-size:13px;'
            f'color:{spec["title_color"]};line-height:1;">'
            "<span>–</span><span>□</span><span>×</span></span>"
        )
    else:  # gnome-button
        left = ""
        right = (
            f'<span style="width:20px;height:20px;border-radius:50%;background:#484848;'
            f"display:inline-flex;align-items:center;justify-content:center;"
            f'font-size:12px;color:{spec["title_color"]};">×</span>'
        )

    return (
        f'<div style="height:{_TITLEBAR_H}px;background:{spec["titlebar_bg"]};'
        "display:flex;align-items:center;justify-content:space-between;"
        "padding:0 14px;box-sizing:border-box;"
        f"font-family:{_FONT_FAMILY};font-size:13px;font-weight:600;"
        f'color:{spec["title_color"]};">'
        f'<div style="flex:1;display:flex;align-items:center;">{left}</div>'
        f'<div style="flex:2;text-align:center;white-space:nowrap;'
        f'overflow:hidden;text-overflow:ellipsis;">{_html_escape(title)}</div>'
        f'<div style="flex:1;display:flex;align-items:center;'
        f'justify-content:flex-end;">{right}</div>'
        "</div>"
    )


def render_html(
    app,
    *,
    title: str | None = None,
    frame: str | None = None,
    standalone: bool = False,
) -> str:
    """Render `app`'s current screen as a standalone HTML document. `frame`
    ("macos"/"windows"/"gnome") wraps the terminal in a fake OS window
    (titlebar, rounded corners, drop shadow), same as `render_svg`.
    `standalone=True` goes further: a dark, centered page around it (so
    opening the file looks like a presentable screenshot, not text in a
    corner) that also scrolls instead of overflowing on narrow viewports."""
    _validate_frame(frame)
    base_fg, base_bg = _base_colors(app)
    title = title or app.title or "Cozy TUI"
    body = _content_html_body(app, base_fg, base_bg)
    term_pre = (
        f'<pre style="margin:0;padding:1em;color:{base_fg};'
        f"background:{base_bg};font-family:{_FONT_FAMILY};"
        f'font-size:{_FONT_SIZE}px;line-height:{_CELL_H}px;">'
        f"{body}</pre>"
    )

    if frame is not None:
        spec = _FRAMES[frame]
        window_html = (
            f'<div style="display:inline-block;border-radius:{spec["radius"]}px;'
            f'overflow:hidden;border:1px solid {spec["border"]};'
            'box-shadow:0 12px 28px rgba(0,0,0,.35);">'
            f"{_titlebar_html(spec, title)}{term_pre}</div>"
        )
    else:
        window_html = term_pre

    if not standalone:
        return (
            '<!doctype html>\n<html>\n<head>\n<meta charset="utf-8">\n'
            f"<title>{_html_escape(title)}</title>\n</head>\n"
            f'<body style="margin:0;background:{base_bg}">\n{window_html}\n'
            "</body>\n</html>\n"
        )

    # A plain (frame=None) terminal still gets a soft box on its own page --
    # the frame's own rounded-corners+shadow styling covers it otherwise.
    shell_style = "max-width:96vw;overflow:auto;"
    if frame is None:
        shell_style += "border-radius:10px;box-shadow:0 12px 28px rgba(0,0,0,.45);"

    return (
        '<!doctype html>\n<html>\n<head>\n<meta charset="utf-8">\n'
        f"<title>{_html_escape(title)}</title>\n"
        "<style>html,body{height:100%;margin:0;background:#15151a;}"
        "body{display:flex;align-items:center;justify-content:center;"
        "padding:32px;box-sizing:border-box;}</style>\n</head>\n<body>\n"
        f'<div style="{shell_style}">{window_html}</div>\n'
        "</body>\n</html>\n"
    )
