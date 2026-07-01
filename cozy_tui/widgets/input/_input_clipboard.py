import pyperclip as _pyperclip


def _clipboard_get() -> str:
    try:
        return _pyperclip.paste() or ""
    except Exception:
        return ""


def _clipboard_set(text: str) -> None:
    if not text:
        return
    try:
        _pyperclip.copy(text)
    except Exception:
        pass
