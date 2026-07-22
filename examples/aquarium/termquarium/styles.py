"""Shared Style constants used across TermQuarium's widgets and UI."""

from cozy_tui import Style

TITLE = Style(fg="bright_cyan", styles=["bold"])
STATS = Style(fg="bright_white")
WATER_LINE = Style(fg="bright_blue")
BUBBLE_STYLE = Style(fg="bright_blue")
FOOD_STYLE = Style(fg="yellow")
WOOD_STYLE = Style(fg="yellow")
HEART_STYLE = Style(fg="bright_magenta")
MUTED = Style(fg="bright_black")
VIGNETTE_STYLE = Style(fg="bright_yellow", styles=["bold"])
FOREST_LEAF_STYLES = (
    Style(fg="green"),
    Style(fg="bright_green"),
    Style(fg="yellow"),
)
# The Forest's Tiger Shark (see tank_objects.py's TigerShark) -- bold
# bright-yellow for a tiger's stripes, which also reads as alarm against the
# green scenery and stands apart from the plain-yellow trunk/wood via bold.
TIGER_SHARK_STYLE = Style(fg="bright_yellow", styles=["bold"])
