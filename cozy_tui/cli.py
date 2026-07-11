"""Command-line interface for Cozy TUI.

Usage::

    cozy-tui                          # launch the interactive demo (same as `python -m cozy_tui`)
    cozy-tui --version                # print the installed version
    cozy-tui demo                     # launch the interactive demo
    cozy-tui doctor                   # run environment / capability checks
    cozy-tui info                     # print version + detected terminal capabilities
    cozy-tui run script.py            # run a script (like `python script.py`)
    cozy-tui run --debug script.py    # ...with App(debug=True) enabled, with no code change

``doctor`` is modelled on cozy-kit's Doctor command: it gathers a handful of
checks and renders them as a Rich table.
"""

import argparse
import json
import os
import platform
import runpy
import shutil
import sys
from pathlib import Path
from urllib import request

from cozy_tui import __version__

PYPI_JSON = "https://pypi.org/pypi/cozy-tui/json"


# ── doctor ────────────────────────────────────────────────────────────────────
# A check is a (name, detail, status) tuple where status is:
#   True  -> pass (green ✓), False -> fail (red ✗), None -> advisory (yellow !).
# Only hard failures (status is False) make the command exit non-zero, so a
# missing clipboard backend or an unreachable PyPI is informational, not an error.


def _latest_pypi_version(timeout: float = 5.0) -> str:
    with request.urlopen(PYPI_JSON, timeout=timeout) as response:
        return json.load(response)["info"]["version"]


def gather_checks(check_pypi: bool = True):
    """Collect the doctor report as a list of ``(name, detail, status)`` rows.

    Pure and network-optional (pass ``check_pypi=False``) so it can be unit
    tested without touching the terminal or the network.
    """
    checks = []

    py = platform.python_version()
    checks.append(("Python >= 3.10", py, sys.version_info >= (3, 10)))

    try:
        import cozy_tui  # noqa: F401

        checks.append(("import cozy_tui", __version__, True))
    except Exception as exc:  # pragma: no cover - import can't realistically fail here
        checks.append(("import cozy_tui", str(exc), False))

    try:
        from importlib.metadata import version as _pkg_version

        import rich  # noqa: F401

        checks.append(("rich available", _pkg_version("rich"), True))
    except Exception as exc:
        checks.append(("rich available", str(exc), False))

    try:
        from cozy_tui import clipboard

        backend = clipboard.backend()
        checks.append(
            ("clipboard backend", backend or "unavailable", True if backend else None)
        )
    except Exception as exc:
        checks.append(("clipboard backend", str(exc), None))

    try:
        from cozy_tui import get_color_depth

        checks.append(("color depth", get_color_depth(), True))
    except Exception as exc:
        checks.append(("color depth", str(exc), None))

    try:
        from importlib.metadata import version as _pkg_version

        import PIL  # noqa: F401

        checks.append(("Pillow (Image widget)", _pkg_version("Pillow"), True))
    except Exception:
        checks.append(
            (
                "Pillow (Image widget)",
                "not installed (pip install cozy-tui[image])",
                None,
            )
        )

    if check_pypi:
        try:
            latest = _latest_pypi_version()
            if latest == __version__:
                checks.append(("cozy-tui up to date", latest, True))
            else:
                checks.append(
                    (
                        "cozy-tui latest",
                        f"installed {__version__}, latest {latest}",
                        None,
                    )
                )
        except Exception:
            checks.append(("cozy-tui latest", "unable to reach PyPI", None))

    return checks


def _cmd_doctor(args) -> int:
    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Cozy TUI Doctor")
    table.add_column("Check", style="cyan", justify="left")
    table.add_column("Result", justify="left")

    marks = {
        True: "[green]✓[/green]",
        False: "[red]✗[/red]",
        None: "[yellow]![/yellow]",
    }
    failed = False
    for name, detail, status in gather_checks(check_pypi=not args.offline):
        if status is False:
            failed = True
        table.add_row(name, f"{marks[status]} {detail}")

    console.print(table)
    if failed:
        console.print("[red]Some checks failed.[/red]")
    else:
        console.print("[green]All good![/green]")
    return 1 if failed else 0


# ── info ──────────────────────────────────────────────────────────────────────


def _cmd_info(args) -> int:
    from rich.console import Console
    from rich.table import Table

    from cozy_tui import clipboard, get_color_depth

    cols, rows = shutil.get_terminal_size((80, 24))
    console = Console()
    table = Table(title="Cozy TUI", show_header=False)
    table.add_column(style="cyan")
    table.add_column()
    table.add_row("version", __version__)
    table.add_row("python", platform.python_version())
    table.add_row("platform", f"{platform.system()} {platform.release()}")
    table.add_row("terminal size", f"{cols}x{rows} (cols x rows)")
    table.add_row("color depth", get_color_depth())
    table.add_row("clipboard backend", clipboard.backend() or "unavailable")
    console.print(table)
    return 0


# ── demo ──────────────────────────────────────────────────────────────────────


def _cmd_demo(args) -> int:
    from cozy_tui.demo import main as run_demo

    run_demo()
    return 0


# ── run ───────────────────────────────────────────────────────────────────────


def _cmd_run(args) -> int:
    """Run a user script, like `python script.py`, optionally flipping on
    App(debug=True) for it via an env var (see App.__init__) — so scripts
    don't need a code change to opt in from the command line."""
    script = Path(args.script)
    if not script.is_file():
        print(f"cozy-tui run: no such file: {script}", file=sys.stderr)
        return 1

    if args.debug:
        os.environ["COZY_TUI_DEBUG"] = "1"

    # Match `python script.py`: argv[0] is the script, the rest is its own;
    # its directory goes on sys.path so its own sibling imports resolve.
    sys.argv = [str(script), *args.script_args]
    script_dir = str(script.resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    runpy.run_path(str(script), run_name="__main__")
    return 0


# ── entry point ───────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cozy-tui",
        description="Cozy TUI — a lightweight, cross-platform Python TUI library.",
    )
    parser.add_argument(
        "--version", action="version", version=f"cozy-tui {__version__}"
    )
    sub = parser.add_subparsers(dest="command", metavar="{demo,doctor,info,run}")

    p_demo = sub.add_parser("demo", help="launch the interactive showcase")
    p_demo.set_defaults(func=_cmd_demo)

    p_doctor = sub.add_parser("doctor", help="run environment / capability checks")
    p_doctor.add_argument(
        "--offline", action="store_true", help="skip the PyPI version check"
    )
    p_doctor.set_defaults(func=_cmd_doctor)

    p_info = sub.add_parser(
        "info", help="print version and detected terminal capabilities"
    )
    p_info.set_defaults(func=_cmd_info)

    p_run = sub.add_parser("run", help="run a Python script (like `python script.py`)")
    p_run.add_argument("script", help="path to the .py file to run")
    p_run.add_argument(
        "--debug",
        action="store_true",
        help="enable App(debug=True) for the script, with no code change needed",
    )
    p_run.add_argument(
        "script_args",
        nargs=argparse.REMAINDER,
        help="arguments forwarded to the script (as sys.argv[1:])",
    )
    p_run.set_defaults(func=_cmd_run)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        # No subcommand: keep the bare `cozy-tui` / `python -m cozy_tui` launching
        # the demo, matching the library's long-standing behavior.
        return _cmd_demo(args)
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
