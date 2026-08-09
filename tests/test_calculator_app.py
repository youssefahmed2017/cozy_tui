"""Pure-logic tests for the calculator example (examples/calculator_app/calculator.py)."""

import importlib.util
import pathlib

_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "examples"
    / "calculator_app"
    / "calculator.py"
)
_spec = importlib.util.spec_from_file_location("calculator_app", _PATH)
c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c)


def test_eval_handles_basic_arithmetic():
    assert c._eval("2+2") == "4"
    assert c._eval("10/4") == "2.5"


def test_eval_auto_closes_unclosed_parens():
    assert c._eval("sqrt(9") == "3"


def test_eval_factorial_and_power():
    assert c._eval("5!") == "120"
    assert c._eval("2**10") == "1024"


def test_eval_rejects_an_explosive_power_chain_instead_of_freezing():
    # Regression: eval() runs on the app's single render-loop thread, so
    # "9**9**9" (9 ^ 387420489, hundreds of millions of digits) used to have
    # eval() itself compute that number, freezing the whole UI. This must
    # raise quickly instead of hanging -- do_equals() already catches any
    # Exception and shows "Error", so raising is enough to fix the freeze.
    import pytest

    with pytest.raises(OverflowError):
        c._eval("9**9**9")


def test_eval_still_allows_a_reasonably_large_power():
    # Guard against being so conservative it breaks ordinary calculator use.
    assert c._eval("2**64") == str(2**64)


def test_guard_does_not_block_non_power_arithmetic_on_large_literals():
    assert c._eval("999999999*999999999") == str(999999999 * 999999999)
