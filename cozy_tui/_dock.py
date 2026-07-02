"""Shared dock layout: lay widgets out by consuming a shrinking rectangle.

Both `App` and `Box` are containers that start from a rectangle — the screen
for `App`, the interior for `Box`. Each docked widget consumes a band from one
edge of what's left; the cross axis stretches to fill the remaining extent. A
widget docked "fill" claims the entire remaining rectangle. Docks are applied
in the order they were added, so the last non-fill dock sees the smallest rect.
"""

SIDES = ("left", "right", "top", "bottom", "fill")


def dock_layout(items, x, y, w, h, scale):
    """Position each (widget, side, margin) by consuming the (x, y, w, h) rect.

    Coordinates are in the container's own space (absolute cells for `App`,
    interior-relative cells for `Box`). `scale` measures widget natural sizes
    and is handed to each widget's `dock_resize` so fillable widgets can grow.
    """
    for widget, side, margin in items:
        if side == "fill":
            _place(widget, x, y, max(0, w), max(0, h), scale)
            w = h = 0
        elif side == "left":
            band = min(widget.natural_width(scale) + margin, max(0, w))
            _place(widget, x + margin, y, max(0, band - margin), h, scale)
            x += band
            w -= band
        elif side == "right":
            band = min(widget.natural_width(scale) + margin, max(0, w))
            _place(widget, x + w - band, y, max(0, band - margin), h, scale)
            w -= band
        elif side == "top":
            band = min(widget.natural_height(scale) + margin, max(0, h))
            _place(widget, x, y + margin, w, max(0, band - margin), scale)
            y += band
            h -= band
        elif side == "bottom":
            band = min(widget.natural_height(scale) + margin, max(0, h))
            _place(widget, x, y + h - band, w, max(0, band - margin), scale)
            h -= band


def _place(widget, x, y, w, h, scale):
    widget.x = x
    widget.y = y
    widget._dock_rect = (x, y, w, h)  # the slice this widget was given
    widget.dock_resize(w, h, scale)
