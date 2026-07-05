"""`python -m cozy_tui` entry point — dispatches to the CLI.

With no arguments it launches the interactive demo (see `cozy_tui.demo`); with a
subcommand it behaves like the `cozy-tui` console script, e.g.
`python -m cozy_tui doctor`.
"""

import sys

from cozy_tui.cli import main

if __name__ == "__main__":
    sys.exit(main())
