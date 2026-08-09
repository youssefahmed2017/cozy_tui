# Copilot instructions — TermQuarium (examples/aquarium)

Purpose: concise, repo-specific guidance for Copilot CLI / AI sessions targeting the TermQuarium example.

Quick commands

- Run the game (from repo root):
  - python examples/aquarium/aquarium.py
  - cozy-tui run examples/aquarium/aquarium.py

- Build Windows executables (from examples/aquarium/):
  - pyinstaller TermQuarium.spec
  - pyinstaller update.spec
  - iscc TermQuarium.iss  # requires Inno Setup for the installer

- Tests
  - Run this example's tests (all):
    - python -m pytest tests/test_aquarium.py tests/test_termquarium_*.py -q
  - Run a single test or a single test function:
    - python -m pytest tests/test_aquarium.py::test_name -q
    - Or use -k to match by substring: pytest -k "keyword" -q

- Linting/formatters: no repo-wide linter or formatter is configured for this example. Add ruff/flake8/black configs if you want automated linting.

High-level architecture (big picture)

- aquarium.py: tiny entrypoint — read its module docstring first. It wires the `termquarium` package into a running App (screens, input, spawning, main()). The module docstring is a chronological design log that explains priority chains and reasoning for gameplay mechanics.

- termquarium/ package: the game's logic split for testability and clarity:
  - constants.py — single source of tunables, species/shop/treat tables, GAME_VERSION
  - steering.py — pure movement math (unit-testable helpers)
  - fish.py — Fish widget: steering blend, hunger/growth/aging, sleep/housing, drawing
  - relationships.py — pairwise continuous bond scores, record_*() APIs, decay logic
  - economy.py / world.py / save.py / cloud.py / updater.py — economy, day/night, versioned JSON saves, optional cloud sync, and updater logic
  - console.py — Cheat Console; structural parsing (ast.parse + ast.literal_eval), never eval/exec
  - shop.py, inspectors.py, ui.py — UI panels and Shop wiring

Key conventions and gotchas

- Read aquarium.py's docstring before changing behavior that spans modules — it documents "why" and the priority system (fleeing > eating > personality > relaxing > schooling > wandering).

- constants.py is authoritative. Avoid sprinkling hard-coded numeric thresholds elsewhere; prefer constants.

- steering.py functions are pure math intended to be unit-tested in isolation. Keep UI coupling out of these functions.

- Fish.friend and Fish.rival are computed properties (derived from relationships). Do not assign to them directly — mutate relationship scores via relationships APIs.

- Relationships model: each fish pair shares one continuous score in [-100, 100]. Mutate via record_*() and rely on decay_relationships() for long-term drift.

- Tests import aquarium.py via importlib to exercise pure logic. If renaming exports, keep the re-exports used by tests to retain compatibility (tests expect names reachable as aq.<name>).

- Cheat Console parsing: structural AST parsing + ast.literal_eval is mandatory. New console commands must accept literal-only arguments and call the same real code Shop/Inspector use.

- Save files are versioned JSON (termquarium/save.py). Implement migration on load rather than breaking compatibility.

- Windows packaging/updater: installed shortcut runs update.exe (launcher) which stages updates and never blocks play. For releases, bump GAME_VERSION in termquarium/constants.py and MyAppVersion in TermQuarium.iss before building.

Important files to read first

- CLAUDE.md (examples/aquarium/CLAUDE.md) — background, commands, and test guidance for this example
- aquarium.py module docstring — step/phase design log for behaviors
- termquarium/constants.py and termquarium/steering.py — to understand numerical thresholds and steering math

AI assistant / existing rules

- CLAUDE.md exists and contains example-specific guidance — include it when reasoning about gameplay and tests.
- No other AI assistant rule files (.cursorrules, AGENTS.md, .windsurfrules, etc.) were detected in the example's directory tree.

If you want this instruction file expanded

- Add linter/formatter commands and config snippets (pyproject.toml, ruff/flake8/black rules)
- Add CI snippets for running the targeted pytest command(s)

Suggested CI (GitHub Actions)

Create .github/workflows/python-tests.yml with this minimal workflow:

```yaml
name: CI — tests & lint
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python: [3.10, 3.11]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python }}
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r website/api/requirements.txt || true
          pip install pytest ruff black
      - name: Run targeted tests (examples/aquarium)
        run: |
          python -m pytest examples/aquarium/tests/test_aquarium.py -q
      - name: Run ruff (optional)
        run: ruff check . || true
```

Notes: the workflow focuses on the example's tests; expand steps to run the full test matrix or build artifacts as needed.

Recommended formatter / linter snippets

Add a lightweight pyproject.toml at the repo root to standardize formatting and linting:

```toml
[tool.black]
line-length = 88

[tool.ruff]
line-length = 88
select = ["E", "F", "W", "I", "C"]
exclude = [".venv", "dist", "build", "site-packages"]

[tool.isort]
profile = "black"
```

Optional pre-commit (recommended): create .pre-commit-config.yaml to run ruff and black on commit.

Final notes

- If requested, create the actual workflow and pyproject.toml files in this repo and open a small PR that adds them.

---

(End of copilot-instructions.md)
