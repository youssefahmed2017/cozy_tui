"""The `cozy-tui` command-line interface."""

import pytest

from cozy_tui import __version__
from cozy_tui import cli


def test_version_flag_prints_version_and_exits(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_gather_checks_offline_has_no_pypi_row():
    rows = cli.gather_checks(check_pypi=False)
    names = [name for name, _detail, _status in rows]
    assert not any("latest" in n or "up to date" in n for n in names)
    # The core checks are always present and passing in a working install.
    by_name = {name: status for name, _detail, status in rows}
    assert by_name["Python >= 3.10"] is True
    assert by_name["import cozy_tui"] is True
    assert by_name["rich available"] is True


def test_gather_checks_status_values_are_valid():
    for _name, _detail, status in cli.gather_checks(check_pypi=False):
        assert status in (True, False, None)


def test_doctor_command_offline_succeeds(capsys):
    code = cli.main(["doctor", "--offline"])
    assert code == 0  # no hard failures on a working install
    out = capsys.readouterr().out
    assert "Cozy TUI Doctor" in out


def test_info_command_runs(capsys):
    assert cli.main(["info"]) == 0
    out = capsys.readouterr().out
    assert __version__ in out


def test_no_subcommand_launches_demo(monkeypatch):
    called = []
    monkeypatch.setattr("cozy_tui.demo.main", lambda: called.append("demo"))
    assert cli.main([]) == 0
    assert called == ["demo"]


def test_demo_subcommand_launches_demo(monkeypatch):
    called = []
    monkeypatch.setattr("cozy_tui.demo.main", lambda: called.append("demo"))
    assert cli.main(["demo"]) == 0
    assert called == ["demo"]
