from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from cozy_tui.ansi import get_color_depth, set_color_depth
from cozy_tui.app import App
from cozy_tui.events import Key
from cozy_tui.state import State
from cozy_tui.style import Style
from cozy_tui.theme import Theme, get_theme, set_theme

try:
    __version__ = _pkg_version("cozy-tui")
except PackageNotFoundError:  # running from a source tree without an installation
    __version__ = "dev"

# Widgets are intentionally NOT re-exported here — import them from the
# cozy_tui.widgets subpackage, e.g. `from cozy_tui.widgets import Label`.

__all__ = [
    "App",
    "Key",
    "State",
    "Style",
    "Theme",
    "get_color_depth",
    "set_color_depth",
    "get_theme",
    "set_theme",
    "__version__",
]
