"""
Run this directly in Windows Terminal:  python mouse_debug.py
Scroll the mouse wheel a few times, then press Ctrl+C.
It prints the raw bytes received so we can verify the VT sequence format.
"""

import ctypes
import msvcrt
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

kernel32 = ctypes.windll.kernel32
ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

h_in = kernel32.GetStdHandle(-10)
h_out = kernel32.GetStdHandle(-11)
old_in = ctypes.c_ulong()
kernel32.GetConsoleMode(h_in, ctypes.byref(old_in))
old_out = ctypes.c_ulong()
kernel32.GetConsoleMode(h_out, ctypes.byref(old_out))

ok_in = kernel32.SetConsoleMode(h_in, old_in.value | ENABLE_VIRTUAL_TERMINAL_INPUT)
ok_out = kernel32.SetConsoleMode(
    h_out, old_out.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
)
print(f"VT_INPUT set: {bool(ok_in)}   VT_PROCESSING set: {bool(ok_out)}")

# Enable X10 + SGR mouse reporting
sys.stdout.write("\033[?1000h\033[?1006h")
sys.stdout.flush()
print("Mouse tracking enabled. Scroll the mouse wheel, then press Ctrl+C.\n")

try:
    while True:
        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch == "\x03":
                break
            buf = [ch]
            # Drain the rest of whatever arrived together
            deadline = time.monotonic() + 0.05
            while msvcrt.kbhit() or time.monotonic() < deadline:
                if msvcrt.kbhit():
                    buf.append(msvcrt.getwch())
                    deadline = time.monotonic() + 0.05
            hexes = " ".join(f"{ord(c):02x}" for c in buf)
            chars = "".join(
                c if c.isprintable() and c != " " else f"\\x{ord(c):02x}" for c in buf
            )
            print(f"  bytes: {hexes}   chars: {chars}")
except KeyboardInterrupt:
    pass
finally:
    sys.stdout.write("\033[?1006l\033[?1000l")
    sys.stdout.flush()
    kernel32.SetConsoleMode(h_in, old_in.value)
    kernel32.SetConsoleMode(h_out, old_out.value)
    print("\nDone.")
