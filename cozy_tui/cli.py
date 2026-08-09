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
import difflib
from pathlib import Path
from urllib import request

from . import __version__

PYPI_JSON = "https://pypi.org/pypi/cozy-tui/json"

from rich.console import Console

console = Console()

class CozyArgumentParser(argparse.ArgumentParser):
    _logo = '\n\n\x1b[38;2;30;30;46m \x1b[38;2;35;38;58m \x1b[38;2;39;46;71m█\x1b[38;2;44;54;83m█\x1b[38;2;48;62;95m█\x1b[38;2;53;71;107m█\x1b[38;2;58;79;120m█\x1b[38;2;62;87;132m█\x1b[38;2;67;95;144m╗\x1b[38;2;71;103;157m \x1b[38;2;76;111;169m \x1b[38;2;80;119;181m█\x1b[38;2;85;127;194m█\x1b[38;2;90;136;206m█\x1b[38;2;94;144;218m█\x1b[38;2;99;152;230m█\x1b[38;2;103;160;243m█\x1b[38;2;108;168;255m╗\x1b[38;2;109;171;248m \x1b[38;2;110;174;241m \x1b[38;2;111;177;234m█\x1b[38;2;112;180;227m█\x1b[38;2;113;183;220m█\x1b[38;2;114;186;213m█\x1b[38;2;115;189;206m█\x1b[38;2;116;192;199m█\x1b[38;2;116;195;192m█\x1b[38;2;117;198;185m╗\x1b[38;2;118;201;178m \x1b[38;2;119;204;171m█\x1b[38;2;120;207;164m█\x1b[38;2;121;210;157m╗\x1b[38;2;122;213;150m \x1b[38;2;123;216;143m \x1b[38;2;131;215;139m \x1b[38;2;139;214;135m█\x1b[38;2;147;213;131m█\x1b[38;2;155;212;127m╗\x1b[38;2;162;211;123m \x1b[38;2;170;210;119m \x1b[38;2;178;209;115m \x1b[38;2;186;208;111m \x1b[38;2;194;206;107m \x1b[38;2;202;205;103m█\x1b[38;2;210;204;99m█\x1b[38;2;218;203;95m█\x1b[38;2;225;202;91m█\x1b[38;2;233;201;87m█\x1b[38;2;241;200;83m█\x1b[38;2;249;199;79m█\x1b[38;2;248;202;89m█\x1b[38;2;247;204;100m╗\x1b[38;2;247;207;110m \x1b[38;2;246;209;120m█\x1b[38;2;245;212;131m█\x1b[38;2;244;214;141m╗\x1b[38;2;243;217;151m \x1b[38;2;243;219;162m \x1b[38;2;242;222;172m \x1b[38;2;241;224;182m█\x1b[38;2;240;227;192m█\x1b[38;2;239;229;203m╗\x1b[38;2;238;232;213m \x1b[38;2;238;234;223m█\x1b[38;2;237;237;234m█\x1b[38;2;236;239;244m╗\x1b[39m\n\x1b[38;2;30;30;46m \x1b[38;2;35;38;58m█\x1b[38;2;39;46;71m█\x1b[38;2;44;54;83m╔\x1b[38;2;48;62;95m═\x1b[38;2;53;71;107m═\x1b[38;2;58;79;120m═\x1b[38;2;62;87;132m═\x1b[38;2;67;95;144m╝\x1b[38;2;71;103;157m \x1b[38;2;76;111;169m█\x1b[38;2;80;119;181m█\x1b[38;2;85;127;194m╔\x1b[38;2;90;136;206m═\x1b[38;2;94;144;218m═\x1b[38;2;99;152;230m═\x1b[38;2;103;160;243m█\x1b[38;2;108;168;255m█\x1b[38;2;109;171;248m╗\x1b[38;2;110;174;241m \x1b[38;2;111;177;234m╚\x1b[38;2;112;180;227m═\x1b[38;2;113;183;220m═\x1b[38;2;114;186;213m█\x1b[38;2;115;189;206m█\x1b[38;2;116;192;199m█\x1b[38;2;116;195;192m╔\x1b[38;2;117;198;185m╝\x1b[38;2;118;201;178m \x1b[38;2;119;204;171m╚\x1b[38;2;120;207;164m█\x1b[38;2;121;210;157m█\x1b[38;2;122;213;150m╗\x1b[38;2;123;216;143m \x1b[38;2;131;215;139m█\x1b[38;2;139;214;135m█\x1b[38;2;147;213;131m╔\x1b[38;2;155;212;127m╝\x1b[38;2;162;211;123m \x1b[38;2;170;210;119m \x1b[38;2;178;209;115m \x1b[38;2;186;208;111m \x1b[38;2;194;206;107m \x1b[38;2;202;205;103m╚\x1b[38;2;210;204;99m═\x1b[38;2;218;203;95m═\x1b[38;2;225;202;91m█\x1b[38;2;233;201;87m█\x1b[38;2;241;200;83m╔\x1b[38;2;249;199;79m═\x1b[38;2;248;202;89m═\x1b[38;2;247;204;100m╝\x1b[38;2;247;207;110m \x1b[38;2;246;209;120m█\x1b[38;2;245;212;131m█\x1b[38;2;244;214;141m║\x1b[38;2;243;217;151m \x1b[38;2;243;219;162m \x1b[38;2;242;222;172m \x1b[38;2;241;224;182m█\x1b[38;2;240;227;192m█\x1b[38;2;239;229;203m║\x1b[38;2;238;232;213m \x1b[38;2;238;234;223m█\x1b[38;2;237;237;234m█\x1b[38;2;236;239;244m║\x1b[39m\n\x1b[38;2;30;30;46m \x1b[38;2;35;38;58m█\x1b[38;2;39;46;71m█\x1b[38;2;44;54;83m║\x1b[38;2;48;62;95m \x1b[38;2;53;71;107m \x1b[38;2;58;79;120m \x1b[38;2;62;87;132m \x1b[38;2;67;95;144m \x1b[38;2;71;103;157m \x1b[38;2;76;111;169m█\x1b[38;2;80;119;181m█\x1b[38;2;85;127;194m║\x1b[38;2;90;136;206m \x1b[38;2;94;144;218m \x1b[38;2;99;152;230m \x1b[38;2;103;160;243m█\x1b[38;2;108;168;255m█\x1b[38;2;109;171;248m║\x1b[38;2;110;174;241m \x1b[38;2;111;177;234m \x1b[38;2;112;180;227m \x1b[38;2;113;183;220m█\x1b[38;2;114;186;213m█\x1b[38;2;115;189;206m█\x1b[38;2;116;192;199m╔\x1b[38;2;116;195;192m╝\x1b[38;2;117;198;185m \x1b[38;2;118;201;178m \x1b[38;2;119;204;171m \x1b[38;2;120;207;164m╚\x1b[38;2;121;210;157m█\x1b[38;2;122;213;150m█\x1b[38;2;123;216;143m█\x1b[38;2;131;215;139m█\x1b[38;2;139;214;135m╔\x1b[38;2;147;213;131m╝\x1b[38;2;155;212;127m \x1b[38;2;162;211;123m \x1b[38;2;170;210;119m \x1b[38;2;178;209;115m \x1b[38;2;186;208;111m \x1b[38;2;194;206;107m \x1b[38;2;202;205;103m \x1b[38;2;210;204;99m \x1b[38;2;218;203;95m \x1b[38;2;225;202;91m█\x1b[38;2;233;201;87m█\x1b[38;2;241;200;83m║\x1b[38;2;249;199;79m \x1b[38;2;248;202;89m \x1b[38;2;247;204;100m \x1b[38;2;247;207;110m \x1b[38;2;246;209;120m█\x1b[38;2;245;212;131m█\x1b[38;2;244;214;141m║\x1b[38;2;243;217;151m \x1b[38;2;243;219;162m \x1b[38;2;242;222;172m \x1b[38;2;241;224;182m█\x1b[38;2;240;227;192m█\x1b[38;2;239;229;203m║\x1b[38;2;238;232;213m \x1b[38;2;238;234;223m█\x1b[38;2;237;237;234m█\x1b[38;2;236;239;244m║\x1b[39m\n\x1b[38;2;30;30;46m \x1b[38;2;35;38;58m█\x1b[38;2;39;46;71m█\x1b[38;2;44;54;83m║\x1b[38;2;48;62;95m \x1b[38;2;53;71;107m \x1b[38;2;58;79;120m \x1b[38;2;62;87;132m \x1b[38;2;67;95;144m \x1b[38;2;71;103;157m \x1b[38;2;76;111;169m█\x1b[38;2;80;119;181m█\x1b[38;2;85;127;194m║\x1b[38;2;90;136;206m \x1b[38;2;94;144;218m \x1b[38;2;99;152;230m \x1b[38;2;103;160;243m█\x1b[38;2;108;168;255m█\x1b[38;2;109;171;248m║\x1b[38;2;110;174;241m \x1b[38;2;111;177;234m \x1b[38;2;112;180;227m█\x1b[38;2;113;183;220m█\x1b[38;2;114;186;213m█\x1b[38;2;115;189;206m╔\x1b[38;2;116;192;199m╝\x1b[38;2;116;195;192m \x1b[38;2;117;198;185m \x1b[38;2;118;201;178m \x1b[38;2;119;204;171m \x1b[38;2;120;207;164m \x1b[38;2;121;210;157m╚\x1b[38;2;122;213;150m█\x1b[38;2;123;216;143m█\x1b[38;2;131;215;139m╔\x1b[38;2;139;214;135m╝\x1b[38;2;147;213;131m \x1b[38;2;155;212;127m \x1b[38;2;162;211;123m \x1b[38;2;170;210;119m \x1b[38;2;178;209;115m \x1b[38;2;186;208;111m \x1b[38;2;194;206;107m \x1b[38;2;202;205;103m \x1b[38;2;210;204;99m \x1b[38;2;218;203;95m \x1b[38;2;225;202;91m█\x1b[38;2;233;201;87m█\x1b[38;2;241;200;83m║\x1b[38;2;249;199;79m \x1b[38;2;248;202;89m \x1b[38;2;247;204;100m \x1b[38;2;247;207;110m \x1b[38;2;246;209;120m█\x1b[38;2;245;212;131m█\x1b[38;2;244;214;141m║\x1b[38;2;243;217;151m \x1b[38;2;243;219;162m \x1b[38;2;242;222;172m \x1b[38;2;241;224;182m█\x1b[38;2;240;227;192m█\x1b[38;2;239;229;203m║\x1b[38;2;238;232;213m \x1b[38;2;238;234;223m█\x1b[38;2;237;237;234m█\x1b[38;2;236;239;244m║\x1b[39m\n\x1b[38;2;30;30;46m \x1b[38;2;35;38;58m╚\x1b[38;2;39;46;71m█\x1b[38;2;44;54;83m█\x1b[38;2;48;62;95m█\x1b[38;2;53;71;107m█\x1b[38;2;58;79;120m█\x1b[38;2;62;87;132m█\x1b[38;2;67;95;144m╗\x1b[38;2;71;103;157m \x1b[38;2;76;111;169m╚\x1b[38;2;80;119;181m█\x1b[38;2;85;127;194m█\x1b[38;2;90;136;206m█\x1b[38;2;94;144;218m█\x1b[38;2;99;152;230m█\x1b[38;2;103;160;243m█\x1b[38;2;108;168;255m╔\x1b[38;2;109;171;248m╝\x1b[38;2;110;174;241m \x1b[38;2;111;177;234m█\x1b[38;2;112;180;227m█\x1b[38;2;113;183;220m█\x1b[38;2;114;186;213m█\x1b[38;2;115;189;206m█\x1b[38;2;116;192;199m█\x1b[38;2;116;195;192m█\x1b[38;2;117;198;185m╗\x1b[38;2;118;201;178m \x1b[38;2;119;204;171m \x1b[38;2;120;207;164m \x1b[38;2;121;210;157m \x1b[38;2;122;213;150m█\x1b[38;2;123;216;143m█\x1b[38;2;131;215;139m║\x1b[38;2;139;214;135m \x1b[38;2;147;213;131m \x1b[38;2;155;212;127m \x1b[38;2;162;211;123m \x1b[38;2;170;210;119m \x1b[38;2;178;209;115m \x1b[38;2;186;208;111m \x1b[38;2;194;206;107m \x1b[38;2;202;205;103m \x1b[38;2;210;204;99m \x1b[38;2;218;203;95m \x1b[38;2;225;202;91m█\x1b[38;2;233;201;87m█\x1b[38;2;241;200;83m║\x1b[38;2;249;199;79m \x1b[38;2;248;202;89m \x1b[38;2;247;204;100m \x1b[38;2;247;207;110m \x1b[38;2;246;209;120m╚\x1b[38;2;245;212;131m█\x1b[38;2;244;214;141m█\x1b[38;2;243;217;151m█\x1b[38;2;243;219;162m█\x1b[38;2;242;222;172m█\x1b[38;2;241;224;182m█\x1b[38;2;240;227;192m╔\x1b[38;2;239;229;203m╝\x1b[38;2;238;232;213m \x1b[38;2;238;234;223m█\x1b[38;2;237;237;234m█\x1b[38;2;236;239;244m║\x1b[39m\n\x1b[38;2;30;30;46m \x1b[38;2;35;38;58m \x1b[38;2;39;46;71m╚\x1b[38;2;44;54;83m═\x1b[38;2;48;62;95m═\x1b[38;2;53;71;107m═\x1b[38;2;58;79;120m═\x1b[38;2;62;87;132m═\x1b[38;2;67;95;144m╝\x1b[38;2;71;103;157m \x1b[38;2;76;111;169m \x1b[38;2;80;119;181m╚\x1b[38;2;85;127;194m═\x1b[38;2;90;136;206m═\x1b[38;2;94;144;218m═\x1b[38;2;99;152;230m═\x1b[38;2;103;160;243m═\x1b[38;2;108;168;255m╝\x1b[38;2;109;171;248m \x1b[38;2;110;174;241m \x1b[38;2;111;177;234m╚\x1b[38;2;112;180;227m═\x1b[38;2;113;183;220m═\x1b[38;2;114;186;213m═\x1b[38;2;115;189;206m═\x1b[38;2;116;192;199m═\x1b[38;2;116;195;192m═\x1b[38;2;117;198;185m╝\x1b[38;2;118;201;178m \x1b[38;2;119;204;171m \x1b[38;2;120;207;164m \x1b[38;2;121;210;157m \x1b[38;2;122;213;150m╚\x1b[38;2;123;216;143m═\x1b[38;2;131;215;139m╝\x1b[38;2;139;214;135m \x1b[38;2;147;213;131m \x1b[38;2;155;212;127m \x1b[38;2;162;211;123m \x1b[38;2;170;210;119m \x1b[38;2;178;209;115m \x1b[38;2;186;208;111m \x1b[38;2;194;206;107m \x1b[38;2;202;205;103m \x1b[38;2;210;204;99m \x1b[38;2;218;203;95m \x1b[38;2;225;202;91m╚\x1b[38;2;233;201;87m═\x1b[38;2;241;200;83m╝\x1b[38;2;249;199;79m \x1b[38;2;248;202;89m \x1b[38;2;247;204;100m \x1b[38;2;247;207;110m \x1b[38;2;246;209;120m \x1b[38;2;245;212;131m╚\x1b[38;2;244;214;141m═\x1b[38;2;243;217;151m═\x1b[38;2;243;219;162m═\x1b[38;2;242;222;172m═\x1b[38;2;241;224;182m═\x1b[38;2;240;227;192m╝\x1b[38;2;239;229;203m \x1b[38;2;238;232;213m \x1b[38;2;238;234;223m╚\x1b[38;2;237;237;234m═\x1b[38;2;236;239;244m╝\x1b[39m\n\n\n\x1b[0m\x1b[?25h\x1b[K'

    def print_help(self, file=None):
        from rich.console import Console
        from rich.text import Text

        console = Console(file=file)

        # ── Logo ──────────────────────────────────────────────────────────────
        console.print(Text.from_ansi(self._logo))

        # ── Description ───────────────────────────────────────────────────────
        if self.description:
            console.print(f"[dim]{self.description}[/dim]")
            console.print()

        # ── Usage ─────────────────────────────────────────────────────────────
        console.print("[bold]Usage[/bold]")

        usage = self.format_usage().strip()

        # Remove argparse's "usage:" prefix.
        if usage.lower().startswith("usage:"):
            usage = usage[6:].strip()

        console.print(f"  [yellow]{usage}[/yellow]")

        # ── Commands ──────────────────────────────────────────────────────────
        subparsers = next(
            (
                action
                for action in self._actions
                if isinstance(action, argparse._SubParsersAction)
            ),
            None,
        )

        if subparsers:
            console.print()
            console.print("[bold]Commands[/bold]")

            for action in subparsers._choices_actions:
                name = action.dest
                help_text = action.help or ""

                console.print(
                    f"  [yellow]{name:<12}[/yellow]"
                    f"[dim]{help_text}[/dim]"
                )

        # ── Options ───────────────────────────────────────────────────────────
        options = [
            action
            for action in self._actions
            if action.option_strings
        ]

        if options:
            console.print()
            console.print("[bold]Options[/bold]")

            for action in options:
                flags = ", ".join(action.option_strings)

                console.print(
                    f"  [bold]{flags:<20}[/bold]"
                    f"[dim]{action.help or ''}[/dim]"
                )

        # ── Epilog ────────────────────────────────────────────────────────────
        if self.epilog:
            console.print()
            console.print(self.epilog)

    def error(self, message):
        prefix = "argument "
        invalid = "invalid choice: "

        if invalid in message:
            value = message.split(invalid, 1)[1]
            value = value.split(" ", 1)[0].strip("'\"")

            subparsers = next(
                (
                    action
                    for action in self._actions
                    if isinstance(action, argparse._SubParsersAction)
                ),
                None,
            )

            if subparsers:
                commands = list(subparsers.choices)

                matches = difflib.get_close_matches(
                    value,
                    commands,
                    n=3,
                    cutoff=0.6,
                )

                console.print(
                    f"[bold red]✗ No command named[/bold red] "
                    f"[yellow]`{value}`[/yellow]"
                )

                if matches:
                    console.print()
                    console.print("[bold]Did you mean:[/bold]")
                    for match in matches:
                        console.print(f"  [yellow]• {match}[/yellow]")

                raise SystemExit(2)

        console.print(f"[bold red]✗ Error:[/bold red] {message}")
        raise SystemExit(2)

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
    import locale
    import os
    import platform
    import shutil
    import sys
    from importlib.metadata import version, PackageNotFoundError

    from rich.console import Console
    from rich.table import Table

    from cozy_tui import __version__, clipboard, get_color_depth

    console = Console()

    def value_or_unknown(value):
        if value is None or value == "":
            return "*Unknown*"
        return str(value)

    def env(name):
        return os.environ.get(name, "*Not set*")

    def package_version(name):
        try:
            return version(name)
        except PackageNotFoundError:
            return "*Not installed*"
        except Exception:
            return "*Unknown*"

    def get_os_display_name():
        if platform.system() != "Windows":
            return f"{platform.system()} {platform.release()}"

        build = int(platform.version().split(".")[-1])

        # Windows 11 starts at build 22000
        if build >= 22000:
            return "Windows 11"

        return "Windows 10"

    def table(rows):
        result = Table(show_header=True)
        result.add_column("Name", style="cyan")
        result.add_column("Value")

        for name, value in rows:
            result.add_row(name, value_or_unknown(value))

        console.print(result)
        console.print()

    # ─────────────────────────────────────────────────────────────────────
    # Header
    # ─────────────────────────────────────────────────────────────────────

    console.print()
    console.print("[bold cyan]# Cozy TUI Diagnostics[/bold cyan]")
    console.print()

    # ─────────────────────────────────────────────────────────────────────
    # Versions
    # ─────────────────────────────────────────────────────────────────────

    console.print("[bold]## Versions[/bold]")

    table([
        ("Cozy TUI", __version__),
        ("Rich", package_version("rich")),
        ("Pillow", package_version("Pillow")),
    ])

    # ─────────────────────────────────────────────────────────────────────
    # Python
    # ─────────────────────────────────────────────────────────────────────

    console.print("[bold]## Python[/bold]")

    table([
        ("Version", platform.python_version()),
        ("Implementation", platform.python_implementation()),
        ("Compiler", platform.python_compiler()),
        ("Executable", sys.executable),
        ("Prefix", sys.prefix),
        ("Base prefix", sys.base_prefix),
        ("Exec prefix", sys.exec_prefix),
        ("Base exec prefix", sys.base_exec_prefix),
        ("Architecture", platform.architecture()[0]),
        ("Build", platform.python_build()),
        ("Branch", platform.python_branch()),
        ("Revision", platform.python_revision()),
        ("Debug build", hasattr(sys, "gettotalrefcount")),
        ("Byte order", sys.byteorder),
        ("Filesystem encoding", sys.getfilesystemencoding()),
        ("Default encoding", sys.getdefaultencoding()),
        ("Stdout encoding", getattr(sys.stdout, "encoding", None)),
        ("Stderr encoding", getattr(sys.stderr, "encoding", None)),
    ])

    # ─────────────────────────────────────────────────────────────────────
    # Operating System
    # ─────────────────────────────────────────────────────────────────────

    console.print("[bold]## Operating System[/bold]")

    uname = platform.uname()

    table([
        ("System", get_os_display_name()),
        ("Release", platform.release()),
        ("Version", platform.version()),
        ("Machine", platform.machine()),
        ("Processor", platform.processor()),
        ("Architecture", platform.architecture()[0]),
        ("Hostname", platform.node()),
        ("Platform", platform.platform()),
        ("Uname system", uname.system),
        ("Uname release", uname.release),
        ("Uname version", uname.version),
        ("Uname machine", uname.machine),
        ("Uname processor", uname.processor),
    ])

    # ─────────────────────────────────────────────────────────────────────
    # Terminal
    # ─────────────────────────────────────────────────────────────────────

    console.print("[bold]## Terminal[/bold]")

    terminal_size = shutil.get_terminal_size((80, 24))

    table([
        ("Terminal Application", env("TERM_PROGRAM")),
        ("TERM", env("TERM")),
        ("COLORTERM", env("COLORTERM")),
        ("FORCE_COLOR", env("FORCE_COLOR")),
        ("NO_COLOR", env("NO_COLOR")),
        ("TERM_PROGRAM_VERSION", env("TERM_PROGRAM_VERSION")),
        ("WT_SESSION", env("WT_SESSION")),
        ("ConEmuANSI", env("ConEmuANSI")),
        ("ANSICON", env("ANSICON")),
        ("CI", env("CI")),
        ("Terminal size", f"{terminal_size.columns} × {terminal_size.lines}"),
        ("Color depth", get_color_depth()),
        ("Clipboard backend", clipboard.backend() or "unavailable"),
    ])

    # ─────────────────────────────────────────────────────────────────────
    # Environment
    # ─────────────────────────────────────────────────────────────────────

    console.print("[bold]## Environment[/bold]")

    table([
        ("SHELL", env("SHELL")),
        ("COMSPEC", env("COMSPEC")),
        ("SystemRoot", env("SystemRoot")),
        ("TEMP", env("TEMP")),
        ("TMP", env("TMP")),
        ("HOME", env("HOME")),
        ("USERPROFILE", env("USERPROFILE")),
        ("VIRTUAL_ENV", env("VIRTUAL_ENV")),
        ("PYTHONPATH", env("PYTHONPATH")),
        ("PYTHONHOME", env("PYTHONHOME")),
        ("PYTHONUTF8", env("PYTHONUTF8")),
        ("PYTHONIOENCODING", env("PYTHONIOENCODING")),
    ])

    # ─────────────────────────────────────────────────────────────────────
    # Process
    # ─────────────────────────────────────────────────────────────────────

    console.print("[bold]## Process[/bold]")

    table([
        ("PID", os.getpid()),
        ("Parent PID", os.getppid()),
        ("Command", sys.argv[0]),
        ("Arguments", " ".join(sys.argv[1:]) or "*None*"),
        ("Interactive", sys.flags.interactive),
        ("Optimize", sys.flags.optimize),
        ("Isolated", sys.flags.isolated),
        ("Ignore environment", sys.flags.ignore_environment),
        ("No user site", sys.flags.no_user_site),
        ("UTF-8 mode", sys.flags.utf8_mode),
        ("Hash randomization", sys.flags.hash_randomization),
        ("Recursion limit", sys.getrecursionlimit()),
    ])

    # ─────────────────────────────────────────────────────────────────────
    # Paths
    # ─────────────────────────────────────────────────────────────────────

    console.print("[bold]## Paths[/bold]")

    table([
        ("Working directory", os.getcwd()),
        ("Python executable", sys.executable),
        ("sys.prefix", sys.prefix),
        ("sys.base_prefix", sys.base_prefix),
        ("sys.exec_prefix", sys.exec_prefix),
        ("sys.path", os.pathsep.join(sys.path)),
    ])

    # ─────────────────────────────────────────────────────────────────────
    # Locale
    # ─────────────────────────────────────────────────────────────────────

    console.print("[bold]## Locale[/bold]")

    try:
        language = locale.getlocale(locale.LC_CTYPE)
    except Exception:
        language = None

    try:
        preferred_encoding = locale.getpreferredencoding(False)
    except Exception:
        preferred_encoding = None

    table([
        ("Locale", language),
        ("Preferred encoding", preferred_encoding),
        ("Filesystem encoding", sys.getfilesystemencoding()),
        ("Default encoding", sys.getdefaultencoding()),
    ])

    # ─────────────────────────────────────────────────────────────────────
    # Hardware
    # ─────────────────────────────────────────────────────────────────────

    console.print("[bold]## Hardware[/bold]")

    table([
        ("CPU", platform.processor()),
        ("Machine", platform.machine()),
        ("Architecture", platform.architecture()[0]),
        ("CPU count", os.cpu_count()),
    ])

    # ─────────────────────────────────────────────────────────────────────
    # Rich Console options
    # ─────────────────────────────────────────────────────────────────────

    console.print("[bold]## Rich Console options[/bold]")

    table([
        ("size", f"width={console.width}, height={console.height}"),
        ("legacy_windows", console.legacy_windows),
        ("min_width", console.options.min_width),
        ("max_width", console.options.max_width),
        ("is_terminal", console.is_terminal),
        ("encoding", console.encoding),
        ("max_height", console.options.max_height),
        ("justify", console.options.justify),
        ("overflow", console.options.overflow),
        ("no_wrap", console.options.no_wrap),
        ("highlight", console.options.highlight),
        ("markup", console.options.markup),
        ("height", console.options.height),
    ])

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
        console.print(
            f"[bold red]✗ File not found:[/bold red] "
            f"[yellow]`{script}`[/yellow]",
        )
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
    parser = CozyArgumentParser(
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
        return parser.print_help()
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
