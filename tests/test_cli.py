"""The `cozy-tui` command-line interface."""

import os

import pytest

from cozy_tui import __version__, cli


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


# ── run ───────────────────────────────────────────────────────────────────────


def _write_script(tmp_path, body):
    script = tmp_path / "script.py"
    script.write_text(body, encoding="utf-8")
    return script


def test_run_missing_script_errors_without_raising(tmp_path, capsys):
    code = cli.main(["run", str(tmp_path / "ghost.py")])
    assert code == 1
    assert "no such file" in capsys.readouterr().err


def test_run_executes_the_script_as_main(tmp_path, capsys):
    script = _write_script(tmp_path, "print('name=' + __name__)")
    assert cli.main(["run", str(script)]) == 0
    assert "name=__main__" in capsys.readouterr().out


def test_run_forwards_argv_to_the_script(tmp_path, capsys):
    script = _write_script(
        tmp_path, "import sys\nprint(sys.argv[0]); print(sys.argv[1:])"
    )
    assert cli.main(["run", str(script), "foo", "--bar"]) == 0
    out = capsys.readouterr().out
    assert str(script) in out  # argv[0] printed as a plain string, not repr'd
    assert "['foo', '--bar']" in out


def test_run_without_debug_leaves_app_debug_off(tmp_path, capsys):
    os.environ.pop("COZY_TUI_DEBUG", None)  # ensure a clean baseline; see note above
    script = _write_script(
        tmp_path,
        "from cozy_tui import App\n"
        "app = App(full=False, size='200x50')\n"
        "print('debug_log_is_none=' + str(app._debug_log is None))",
    )
    assert cli.main(["run", str(script)]) == 0
    assert "debug_log_is_none=True" in capsys.readouterr().out
    assert "COZY_TUI_DEBUG" not in os.environ


def test_run_with_debug_flag_enables_app_debug(tmp_path, capsys):
    # _cmd_run sets os.environ directly (that's the whole point — it must
    # survive into the script's own `import os`), so monkeypatch never tracks
    # it as "its" change. Calling monkeypatch.delenv on it would actually
    # schedule monkeypatch to *restore* that leftover "1" at teardown (delenv
    # remembers "put back whatever was there") — plain os.environ.pop is the
    # only way to truly clear it here, both before and after.
    os.environ.pop("COZY_TUI_DEBUG", None)
    script = _write_script(
        tmp_path,
        "from cozy_tui import App\n"
        "app = App(full=False, size='200x50')\n"
        "print('debug_log_is_none=' + str(app._debug_log is None))",
    )
    try:
        assert cli.main(["run", "--debug", str(script)]) == 0
        assert "debug_log_is_none=False" in capsys.readouterr().out
        assert os.environ["COZY_TUI_DEBUG"] == "1"
    finally:
        os.environ.pop("COZY_TUI_DEBUG", None)


def test_run_explicit_debug_false_overrides_env_var(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("COZY_TUI_DEBUG", "1")
    script = _write_script(
        tmp_path,
        "from cozy_tui import App\n"
        "app = App(full=False, size='200x50', debug=False)\n"
        "print('debug_log_is_none=' + str(app._debug_log is None))",
    )
    assert cli.main(["run", str(script)]) == 0
    assert "debug_log_is_none=True" in capsys.readouterr().out
