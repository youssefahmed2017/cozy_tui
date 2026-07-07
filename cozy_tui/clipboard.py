"""Minimal cross-platform clipboard for cozy_tui.

This exposes exactly what the library needs — `copy(text)` and `paste() -> str`
— and deliberately is *not* a full pyperclip replacement. It is best-effort: if
no clipboard backend is available, `copy()` falls back to an OSC 52 terminal
escape (or does nothing) and `paste()` returns "". Both swallow errors and never
raise, which is the contract the input widgets rely on. The backend is detected
once at import.

Backends, in preference order:
  * Windows : Win32 clipboard API via ctypes (native, no subprocess).
  * macOS   : pbcopy / pbpaste.
  * Linux/* : wl-copy + wl-paste (Wayland) -> xclip -> xsel (X11).
  * Fallback: OSC 52 escape for copy; paste is unsupported (returns "").
"""

from __future__ import annotations

import base64
import shutil
import subprocess
import sys

__all__ = ["copy", "paste", "available", "backend"]


def copy(text: str) -> None:
    """Best-effort copy of `text` to the system clipboard. Never raises."""
    try:
        _COPY(str(text))
    except Exception:
        pass


def paste() -> str:
    """Best-effort read of the system clipboard, or "" if unavailable. Never raises."""
    try:
        return _PASTE() or ""
    except Exception:
        return ""


def available() -> bool:
    """True if the detected backend supports both copy and paste (i.e. a
    round-trip works). False for the OSC 52 / no-backend fallback."""
    return _CAN_PASTE


def backend() -> str:
    """Name of the selected backend: one of "win32", "pbcopy", "wl-clipboard",
    "xclip", "xsel", or "osc52". Useful for diagnostics and CI assertions."""
    return _BACKEND


# ── backends ─────────────────────────────────────────────────────────────────


def _osc52_copy(text: str) -> None:
    payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
    sys.stdout.write(f"\033]52;c;{payload}\a")
    sys.stdout.flush()


def _null_paste() -> str:
    return ""


# Both copy() and paste() run synchronously on the main UI thread (from
# Ctrl+C/Ctrl+V key handling), so a hung clipboard tool (e.g. a Wayland
# compositor that never hands off ownership) must not freeze the app forever.
_CLI_TIMEOUT = 2.0


def _cli_copier(cmd):
    def _copy(text: str) -> None:
        subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=_CLI_TIMEOUT,
        )

    return _copy


def _cli_paster(cmd):
    def _paste() -> str:
        out = subprocess.run(
            cmd, capture_output=True, check=False, timeout=_CLI_TIMEOUT
        ).stdout
        return out.decode("utf-8", "replace")

    return _paste


def _win_backend():
    """Return (copy, paste, True) using the Win32 clipboard API, or raise."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    # Explicit signatures keep handles/pointers 64-bit safe.
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL

    def _open() -> bool:
        # The clipboard is a shared resource; another app may hold it briefly.
        for _ in range(10):
            if user32.OpenClipboard(None):
                return True
            kernel32.Sleep(5)
        return False

    def _copy(text: str) -> None:
        if not _open():
            return
        try:
            user32.EmptyClipboard()
            buf = ctypes.create_unicode_buffer(text)  # NUL-terminated wide string
            size = ctypes.sizeof(buf)
            handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
            if not handle:
                return
            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                kernel32.GlobalFree(handle)
                return
            ctypes.memmove(ptr, buf, size)
            kernel32.GlobalUnlock(handle)
            # On success the system owns `handle`; it must not be freed here. But
            # if SetClipboardData fails, ownership never transferred — free it.
            if not user32.SetClipboardData(CF_UNICODETEXT, handle):
                kernel32.GlobalFree(handle)
                return
        finally:
            user32.CloseClipboard()

    def _paste() -> str:
        if not _open():
            return ""
        try:
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ""
            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                return ""
            try:
                return ctypes.wstring_at(ptr)
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()

    return _copy, _paste, True


def _select_backend():
    """Return (copy, paste, can_paste, name) for the best available backend."""
    if sys.platform == "win32":
        try:
            copy, paste, ok = _win_backend()
            return copy, paste, ok, "win32"
        except Exception:
            return _osc52_copy, _null_paste, False, "osc52"

    if sys.platform == "darwin":
        if shutil.which("pbcopy") and shutil.which("pbpaste"):
            return _cli_copier(["pbcopy"]), _cli_paster(["pbpaste"]), True, "pbcopy"
    else:  # Linux, *BSD, and other POSIX
        if shutil.which("wl-copy") and shutil.which("wl-paste"):
            return (
                _cli_copier(["wl-copy"]),
                _cli_paster(["wl-paste", "--no-newline"]),
                True,
                "wl-clipboard",
            )
        if shutil.which("xclip"):
            return (
                _cli_copier(["xclip", "-selection", "clipboard"]),
                _cli_paster(["xclip", "-selection", "clipboard", "-o"]),
                True,
                "xclip",
            )
        if shutil.which("xsel"):
            return (
                _cli_copier(["xsel", "-b", "-i"]),
                _cli_paster(["xsel", "-b", "-o"]),
                True,
                "xsel",
            )

    return _osc52_copy, _null_paste, False, "osc52"


_COPY, _PASTE, _CAN_PASTE, _BACKEND = _select_backend()
