from cozy_tui import _console


def test_flush_input_does_not_raise():
    # Only guarantee: never raises, even outside a real console/tty (as in CI).
    _console.flush_input()
