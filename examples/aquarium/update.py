"""TermQuarium's updating launcher -- the target the desktop shortcut points at
instead of TermQuarium.exe.

    shortcut -> update.exe
      1. apply any update staged on a previous run   (instant, local swap)
      2. launch the game                             (inherits the terminal)
      3. once a day, in the background, check for and stage a newer build
         for next time                               (never blocks startup)

Almost all the thinking lives in `termquarium/updater.py`; this file is just
the glue that resolves paths, spawns the detached background check, and hands
the terminal to the game. It is written to never crash *before* the game
launches -- an updater that stops you playing is worse than a stale build.

Run modes:
    python update.py                # normal: apply, launch, maybe check
    python update.py --skip         # launch immediately, no update check
    python update.py --background   # (internal) run one check + stage, then exit

Packaging: build this with PyInstaller as `update.exe` alongside the game's
own `TermQuarium.exe`. Install per-user (e.g. %LOCALAPPDATA%) so staging a new
build never needs an admin/UAC prompt -- see project memory for the rationale.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Allow `from termquarium...` whether run as a loose script or a frozen exe.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from termquarium import updater
from termquarium.constants import GAME_VERSION

# Passed to the game's process so it can, if it wants, toast "Updated to vX 🎉"
# and show release notes on first launch after a swap (see project memory).
UPDATED_ENV_VAR = "TERMQUARIUM_UPDATED_TO"


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def install_dir() -> Path:
    """The directory holding the launcher and the game exe (writable, per the
    per-user install plan). In a dev checkout that's this script's folder."""
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _game_command(forwarded: list[str]) -> list[str]:
    """The command that runs the game, inheriting our terminal."""
    if _is_frozen():
        return [str(install_dir() / updater.DEFAULT_EXE_NAME), *forwarded]
    # Dev checkout: no frozen exe, so run the game module with this interpreter.
    return [sys.executable, str(install_dir() / "aquarium.py"), *forwarded]


def _spawn_background_check() -> None:
    """Launch a fully detached process to check + stage an update, so the
    download runs alongside the game and blocks nothing. Best-effort: if the
    OS won't let us spawn it, we simply don't check this run."""
    if _is_frozen():
        command = [sys.executable, "--background"]  # the frozen exe re-invokes itself
    else:
        command = [sys.executable, str(Path(__file__).resolve()), "--background"]
    kwargs: dict = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "cwd": str(install_dir()),
    }
    try:
        if os.name == "nt":
            # DETACHED_PROCESS | CREATE_NO_WINDOW: no console flashes up, and it
            # outlives us cleanly.
            kwargs["creationflags"] = 0x00000008 | 0x08000000
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(command, **kwargs)
    except OSError:
        pass


def _run_background_check() -> int:
    """The `--background` entry point (its own detached process)."""
    root = install_dir()
    state_path = root / updater.STATE_FILENAME
    state = updater.load_state(state_path)
    updater.run_background_check(GAME_VERSION, state, root)
    updater.save_state(state, state_path)
    return 0


def main(argv: list[str]) -> int:
    if "--background" in argv:
        return _run_background_check()

    skip = "--skip" in argv
    forwarded = [a for a in argv if a not in ("--skip",)]

    root = install_dir()
    state_path = root / updater.STATE_FILENAME
    env = dict(os.environ)

    # Phase 1 + decision -- guarded so nothing here can stop the game launching.
    try:
        state = updater.load_state(state_path)
        plan = updater.plan_launch(
            GAME_VERSION, state, updater._utc_now(), skip_check=skip
        )
        if plan.apply_pending:
            applied = updater.apply_pending(state, root)
            updater.save_state(state, state_path)
            if applied:
                env[UPDATED_ENV_VAR] = applied
        if plan.check_now:
            _spawn_background_check()
    except Exception:
        # Any unexpected failure in the update path is non-fatal: fall straight
        # through to launching whatever is installed.
        pass

    # Phase 2 -- hand the terminal to the game and wait for it, so the TUI owns
    # the console for its whole session. Propagate its exit code.
    try:
        completed = subprocess.run(_game_command(forwarded), env=env)
        return completed.returncode
    except FileNotFoundError:
        sys.stderr.write("Couldn't find TermQuarium to launch.\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
