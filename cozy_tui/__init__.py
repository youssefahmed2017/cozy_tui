from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from cozy_tui.ansi import get_color_depth, set_color_depth
from cozy_tui.app import App
from cozy_tui.events import Key
from cozy_tui.style import Style

try:
    __version__ = _pkg_version("cozy-tui")
except PackageNotFoundError:  # running from a source tree without an installation
    __version__ = "dev"

# Widgets are intentionally NOT re-exported here — import them from the
# cozy_tui.widgets subpackage, e.g. `from cozy_tui.widgets import Label`.

__all__ = [
    "App",
    "Key",
    "Style",
    "get_color_depth",
    "set_color_depth",
    "__version__",
]
