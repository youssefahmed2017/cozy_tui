# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Scoped to `examples/aquarium/` (TermQuarium). Read the root `CLAUDE.md` first for
`cozy_tui` itself — this file only covers what's specific to this example.

## Commands

```bash
python examples/aquarium/aquarium.py         # run the game (from repo root)
cozy-tui run examples/aquarium/aquarium.py   # same, via the CLI
python -m pytest tests/test_aquarium.py tests/test_termquarium_*.py -q   # this example's tests only
```

No extra dependency beyond `cozy_tui` itself — everything below is stdlib,
with one exception: the Cheat Console's `run()` command (arbitrary-ish
scripted commands, sandboxed by RestrictedPython — see
`termquarium/console.py`) needs `pip install RestrictedPython`, lazily
imported only inside that one command. Every other console command, and
the rest of the game, works with nothing installed beyond `cozy_tui`.

Packaging (Windows `.exe`, from inside `examples/aquarium/`; `*.spec`/`*.iss` are
git-ignored — they exist locally when you're building, not in the checked-out tree):
```bash
pyinstaller TermQuarium.spec   # -> dist/TermQuarium.exe (the game)
pyinstaller update.spec        # -> dist/update.exe (the launcher, see below)
iscc TermQuarium.iss           # -> Output/TermQuarium-Setup.exe (needs Inno Setup)
```

## The one thing to read first

**`aquarium.py`'s module docstring is a chronological "Step N / Phase N" design
log** — every mechanic's *why*, in the order it was built, including the
priority chains that decide what a fish does each frame (e.g. fleeing beats
eating beats personality-steering beats relaxing beats schooling beats plain
wandering). Read the relevant Step/Phase before touching steering,
relationships, sleep, or the economy — the reasoning for non-obvious choices
(why relaxing is cheap steering and not pathfinding, why a housed fish is
invisible rather than just frozen, why Sleepy stacks with personality instead
of replacing it) lives there and nowhere else.

`aquarium.py` itself is deliberately thin: screens, input, spawning, and the
glue that wires `termquarium/`'s systems into one running `App` — `main()`.
Every reusable/testable piece (pure math, widgets, modal-builder functions)
lives in the package instead. `tests/test_aquarium.py` imports `aquarium.py`
directly via `importlib` (not the package) so every name re-exported there
stays reachable as `aq.<name>` — keep those re-exports in the import block at
the top of the file if you rename something they depend on.

## `termquarium/` module map

- **`constants.py`** (~1500 lines) — every tunable threshold, plus the
  species/shop/treat tables. Most constants carry a comment explaining *why*
  that value/ordering, not just what it is — the hunger-band thresholds and
  `GAME_VERSION` (kept in step with `TermQuarium.iss`'s `MyAppVersion` and
  `website/version.json`) are good examples. Check here before hardcoding a
  number anywhere else.
- **`steering.py`** — pure movement math (`steer()` wall-bounce, velocity
  helpers), no `Widget`/`App` involved. This and `bubbles.py`'s
  `rise_bubble()`/`leaves.py`'s `fall_leaf()` are the pattern for keeping game
  math unit-testable: a pure function the widget's `draw()`/tick handler
  calls, tested with plain numbers in `tests/`.
- **`fish.py`** — the `Fish` widget: steering blend, hunger/growth/aging,
  personality, sleep/housing, and its own `draw()`, all in one place since
  they interact constantly. `Fish.friend`/`Fish.rival` are read-only
  properties derived from `relationships.best_bond()`/`worst_bond()` — don't
  assign to them directly, mutate the relationship score instead.
- **`relationships.py`** — personality/Sleepy rolls, breeding, and the
  relationship-score model: every *pair* of fish shares one continuous score
  in `[-100, 100]`, nudged by `record_*()` calls at the moment something
  happens (waking a friend, sleeping together, a shark rescue, ...), decaying
  slowly toward 0 (`decay_relationships()`, once a day), never shown to the
  player as a number — only via `relationship_state()` (Rival/Dislikes/
  Neutral/Friend/Best Friend) plus recent reasons. Bonds are earned, never
  rolled at birth — a new fish starts with none.
- **`economy.py`** — money/food/visitor math (attractiveness, donations,
  welfare eligibility) as plain functions over primitives, called from
  `aquarium.py`'s daily tick.
- **`world.py`** — day/night + water temperature off one shared 0..1
  day-progress fraction, so the two never drift out of sync with separately
  tuned schedules.
- **`shop.py`** / **`console.py`** — two different "typed command" surfaces.
  `shop.py` is the Shop overlay's plain Button wiring. `console.py` is the
  backtick Cheat Console for jumping straight to a test scenario; its
  `parse_command()` is structural (`ast.parse(mode="eval")` + per-argument
  `ast.literal_eval()`) — **never** `eval`/`exec`. Keep any new command
  literal-only; it must call the same real code the Shop/Inspector use, not a
  cheat-only shortcut.
- **`inspectors.py`** / **`ui.py`** / **`styles.py`** — Box-building panel
  functions (Fish/Decoration Inspector, Daily Summary, Settings), small
  reusable UI pieces, and shared `Style` constants. No state lives here.
- **`tank_objects.py`** — non-Fish tank contents: `Food` (plain pellets and
  Inspector-fed treats share the same class, distinguished by `kind`/
  `on_eaten`), foraged Wood, Decorations (furniture; `capacity` > 0 is what
  makes one a sleep-in container — no separate class for that), the Forest's
  Tiger Shark.
- **`bubbles.py`** / **`leaves.py`** / **`dreams.py`** / **`vignettes.py`** —
  ambience: rising bubbles, falling Forest leaves, sleeping fish's dream
  selection/animated view, and the in-tank half of the morning wake-up
  vignette (the toast is the other half, built in `relationships.py`).
- **`save.py`** — versioned plain-JSON saves under `~/.termquarium/saves/`
  (`SAVE_VERSION`, `safe_filename()`). The format is deliberately inspectable
  and shareable — migrate old saves forward on load rather than breaking
  compatibility.
- **`cloud.py`** + **`website/api/`** — optional cloud saves. Client side is
  stdlib `urllib` run on `app.run_worker()` threads (no asyncio — `cozy_tui`
  doesn't have async support). Auth is a single locally-generated **Cloud
  Key** sent as `Authorization: Bearer …` and used directly as the storage
  namespace: no accounts, no login, no password reset — losing the key loses
  the saves. The server (`website/api/index.py` routing + `store.py` logic)
  is a FastAPI app deployed as one Vercel Python function; `index.py`'s
  `_safe_name()` intentionally *duplicates* `save.py`'s sanitization rather
  than importing it, since the two deploy separately.
- **`update.py`** (repo root of this dir) + **`termquarium/updater.py`** —
  the Windows auto-updater. Desktop shortcuts launch `update.exe`, never
  `TermQuarium.exe` directly, because Windows can't overwrite a running
  executable: `update.py` applies any already-staged, checksum-verified
  update (fast local swap), launches the game, then at most once every 24h
  spawns a *detached* background check against
  `termquarium.vercel.app/version.json` that stages (doesn't apply) any
  newer build for next launch. Written to never crash before the game
  launches — an updater that blocks play is worse than a stale build.

## Testing conventions specific to this example

Same house rules as the rest of the repo (see root `CLAUDE.md`), plus:
- `tests/test_aquarium.py` and every `tests/test_termquarium_*.py` load
  `aquarium.py`/the `termquarium/` modules via `importlib.util.spec_from_file_location`
  and test them as **pure logic** — no `App`/`Widget`/`Harness` involved, since
  none of `steering.py`/`economy.py`/`relationships.py`/`world.py`'s core
  functions need one. Reach for the `Harness` only if you're adding a test
  that actually needs to drive the running `App` (input dispatch, focus,
  screens) rather than the math underneath it.
- Current coverage: `test_aquarium.py` (steering/movement), `_world`,
  `_save`, `_console`, `_cloud`, `_cloud_api`, `_updater`.
