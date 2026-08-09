# Roadmap

Planned architectural work that's bigger than a changelog entry. Each section
is a design, not a promise of a ship date — see the linked issue/PR once work
starts.

## Async I/O support

**Goal:** let application code `await` things (HTTP calls, cloud saves, any
I/O-bound work) without spinning up one OS thread per call, the way
`examples/aquarium/termquarium/cloud.py` currently has to via
`app.run_worker()`.

### Where things stand today

`App.run()` (`cozy_tui/app.py:2271-2427`) is a single-threaded loop that
blocks in `wait_input(timeout)` — `select.select` on POSIX, `WaitForSingleObject`
on Windows, both isolated in `cozy_tui/_console.py` — waking for input, timers
(`after`/`every`, hand-rolled `_Timer` + `_drain_timers` on `time.monotonic()`),
or worker results. `run_worker()` runs a plain callable on a daemon thread and
appends `(callback, result)` to a `deque`; the main loop only notices it on its
next wake, bounded by `_IDLE_POLL = 0.1s`. No `asyncio` is used anywhere in the
library today — this is a deliberate choice, not an oversight (see `cloud.py`'s
own docstring).

**Already possible, no library change needed:** `app.run_worker(lambda:
asyncio.run(fetch()))` works right now — a thread running its own throwaway
event loop. The actual gap isn't "can you use async at all," it's that every
concurrent call gets its own OS thread instead of sharing one loop.

### Two constraints that shape the design

1. **Windows can't `select()`/`add_reader()` a console handle the way asyncio
   wants.** `ProactorEventLoop` (the Windows default) only really supports
   sockets/pipes for `add_reader`. Any design that tries to fold the raw
   terminal-input wait itself into asyncio still needs a bridge thread pumping
   console input into the loop on Windows — `_console.py`'s platform split
   doesn't go away.
2. **The test suite's speed depends on the current hand-rolled timers.**
   `Harness.advance()` (`cozy_tui/testing.py:267`) fires `_drain_timers`
   against a virtual clock instantly — nothing in ~1800 tests ever really
   sleeps. `asyncio` has no built-in virtual clock; replacing `_Timer`/
   `_drain_timers` with `loop.call_later` would need a from-scratch fake-clock
   shim to keep that property, and it's easy to get subtly wrong.

### Options considered

- **A — Do nothing.** Already works today (see above); just not ergonomic —
  no shared loop, no first-class API.
- **B — One shared background asyncio loop, zero changes to `run()`.**
  *Chosen — see plan below.*
- **C — Make `run()` itself a coroutine** (`async def run_async()`, `async
  def on_click`, …). The "real" async core loop, but it ripples into every
  dispatch site (`_dispatch_input`, `_dispatch_mouse`, every widget callback)
  needing to detect and schedule coroutines, plus the fake-clock problem
  above. **Rejected for now** — nothing in this codebase does enough
  concurrent I/O-bound work for thread-per-call to be an actual bottleneck,
  so the invasiveness isn't justified. Revisit only if a real use case shows
  up that B can't handle.

### Plan (Option B)

1. Lazily start one daemon thread the first time async is used, running
   `asyncio.new_event_loop().run_forever()`. Not started at all for apps that
   never touch it.
2. Add `App.spawn_async(coro, *, on_result=None, on_error=None)`:
   - `asyncio.run_coroutine_threadsafe(coro, self._async_loop)` to schedule
     the coroutine.
   - A `future.add_done_callback` (invoked on the asyncio thread) that pushes
     `(on_result_or_on_error, value)` onto the **existing** `_worker_results`
     deque — the exact same queue `run_worker` already uses.
   - Returns the `concurrent.futures.Future` (mirrors `run_worker` returning
     its `Thread`), so callers who want to block/cancel can.
3. No changes to `run()`, `_drain_timers`, or the timer system at all —
   `_drain_workers()` already delivers whatever lands in `_worker_results` on
   the main thread, on the loop's normal cadence.
4. **Testing:** `Harness.settle()` (`cozy_tui/testing.py:285`) needs **no
   changes** — it already polls `_drain_workers()`, which is exactly what
   `spawn_async` feeds into. A test can `ui.settle()` after `spawn_async(...)`
   exactly like it does after `run_worker(...)` today.
5. Shut the async loop thread down cleanly on `App.run()`'s exit path
   (alongside the existing terminal-restore `finally` block) if it was ever
   started, so a still-running loop doesn't keep the process alive.

Net effect: many concurrent coroutines (e.g. several simultaneous cloud-save
requests) share one real event loop instead of one OS thread each, delivered
through the exact plumbing `run_worker` already uses — additive, low-risk, no
behavior change for apps that don't use it.

## TermQuarium: Personality System 2.0

**Status: fully shipped**, all five steps below. `Fish.traits`,
`relationships.grant_trait()`, save/load compatibility, the Cheat Console's
`grant_trait()` command, and the Inspector display are all in place for
**Food Lover**, **Dreamer**, **Fast Swimmer**, **Energetic**, **Mischievous**,
and **Keen Explorer** (each with a real, existing-event growth trigger — see
`CHANGELOG.md`). Combination flavor text (step 3) is in too, as a small,
hand-picked table in `inspectors.py` (not every one of the ~50 possible
personality+trait/trait+trait pairs — just the four `updates.md` actually
gave text for). Keen Explorer's "visits new areas first" pitch became "more
eager to go explore the Forest" (`KEEN_EXPLORER_FOREST_CHANCE_MULT`), since
the Forest is the only other area that actually exists to visit.

**Source:** `examples/aquarium/updates.md`, "🧬 Personality System 2.0" and the
sections following it (new personalities, personality interactions,
personality growth) — a design brainstorm, not yet built. This section turns
that brainstorm into a plan grounded in the code as it exists today.

**Goal:** fish personalities stop being one mutually-exclusive string rolled
at birth, and become several independent, stackable traits — some rolled at
birth, some *earned* through play — without a rewrite of every place a
personality is currently checked.

### Where things stand today

`PERSONALITIES = ("Friendly", "Explorer", "Shy", "Greedy", "Lazy", "Playful")`
(`termquarium/constants.py:104`) is a fixed tuple; `random_personality()`
(`termquarium/relationships.py:45`) rolls exactly **one**, uniformly, once
at birth, stored as a plain `self.personality: str`
(`termquarium/fish.py:185`). It's then read via `self.personality == "X"`
scattered across **~28 call sites** in `fish.py`, `relationships.py`, and
`aquarium.py` (steering priority, `_claim_home()`'s container-choice
reordering, wake-up score, forage chance/opt-out, food-seeking speed, …), and
persisted as that same plain string in every save
(`"personality": f.personality`, `aquarium.py:1104`). `tests/test_aquarium.py`
references `.personality` **81 times**. Any change here has to keep old saves
loading and not force a rewrite of that whole test surface just to add one
new trait.

**A stackable trait already exists, and is the template to generalize:**
`Sleepy` (`roll_is_sleepy()`, `termquarium/relationships.py:50`) is already
an independent yes/no trait, rolled separately from `personality` and
explicitly documented as stacking with it ("a Greedy fish can also be
Sleepy"). It only ever gates two things (`find_eligible_waker`/
`resolve_wake_attempt`'s wake-resistance, and dream/vignette flavor) — it
never had to touch the other 28 call sites. Personality System 2.0 is really
"do that, but for more than one trait," not a ground-up rewrite.

### Options considered

- **A — Replace `personality: str` with `traits: set[str]` everywhere**
  (updates.md's literal first suggestion). **Rejected** — this touches all
  ~28 existing call sites, the 81 test references, and the save schema all
  at once, for the same eventual capability as B at much higher risk.
- **B — Keep `personality` exactly as it is; add a second, independent
  `traits: frozenset[str]` alongside it**, generalizing the `is_sleepy`
  pattern from one boolean to several named tags. *Chosen — see plan below.*
- **C — Trait objects** (`Friendly()`, `Dreamer()`, … each a class with its
  own effect methods — updates.md's second suggestion). **Rejected for now**
  — plain string tags checked with `in self.traits` cost exactly as much as
  today's `if self.personality == "X"` chain and stay just as readable at
  six-ish traits; a `Trait` class hierarchy is machinery this doesn't need
  yet (no second consumer of "what does a trait *do*" beyond "which `if`
  branch applies"). Revisit only if traits grow real per-trait state beyond a
  name.

### Plan (Option B)

1. **New traits as tags, not classes.** `Fish.traits: frozenset[str]`,
   default empty. Each of updates.md's proposed additions (Food Lover,
   Dreamer, Energetic, Fast Swimmer, Mischievous, an expanded Explorer bonus)
   becomes one more string checked via `"food_lover" in self.traits` at the
   specific point it matters (hunger-relief bonus, dream-selection weighting
   in `dreams.py`'s `choose_dream()`, steering speed, forage priority, …) —
   additive conditions next to the existing personality checks, not a
   replacement for them.
2. **Traits are earned, not rolled at birth** — deliberately unlike
   `personality`/`Sleepy`. This reuses the exact philosophy
   `relationships.py` already established for Friend/Rival bonds ("earned,
   never rolled") rather than inventing a new one: a `record_trait_gained()`
   sibling to `record_wake_up()`/`record_slept_together()` etc., called at
   the moment something happens (survived a Tiger Shark scare enough times →
   maybe gains a resilience-flavored trait; dreamed about food repeatedly →
   Food Lover; …), logged through the existing `memory_log`
   (`_log_memory()`) so a gained trait shows up the same way an earned
   Friend does. This is also what makes "personality growth" (Day 1: Shy →
   later: Friendly + Shy → later still: + Explorer) fall out for free — it's
   the existing memory/relationship model, applied to one more kind of
   earned state.
3. **Combination flavor text is cosmetic, added last.** Once two or more
   traits can co-occur, small text-only lookups (e.g. Dreamer + Explorer →
   "dreams about places it has never visited") can live in `dreams.py`/
   `inspectors.py` as flavor, matching this codebase's existing "flavor, not
   optimization" thread (Treats/Axolotl/Random Events) — no gameplay effect
   depends on a specific *combination*, only on which individual tags are
   present.
4. **Save compatibility:** `traits` is a new, optional save key. A save
   without one (every existing save) loads as `traits=frozenset()` — a fish
   that simply hasn't earned anything yet, the same default a save-file
   migration elsewhere in this codebase already uses (`shop_out_of_stock`
   backfilled the same way in `_load_snapshot`, `aquarium.py:1220-1223`).
   `personality` itself doesn't move or change shape, so none of the 81
   existing test references need to change.
5. **Cheat Console support**, matching `console.py`'s existing structural
   (`ast.literal_eval`-only) contract: a `grant_trait(fish_name, trait)`
   command calling the same `record_trait_gained()` real code path, for
   testing without waiting on the natural trigger — same pattern
   `start_lost_adventure(...)`-style commands would need for the *other*
   brainstormed system in `updates.md` (Lost Adventure), not part of this
   plan.

Net effect: six-ish new traits, stacking freely with the existing
personality and with each other, earned through play rather than rolled —
without touching the steering-priority chain, `_claim_home()`, or any of the
existing personality-keyed tests.

## TermQuarium: Coral Valley (a second biome)

**Status: the biome itself is still far future — no rooms, no map, no
unlock exist.** Two general-purpose pieces it depends on shipped early
though (see Decisions #2 and #4 below): Keen Explorer's decaying forage
urgency, and day/night phase + in-progress dreams surviving Save/Load. This
section exists so the rest of the idea lives somewhere more permanent than
a scratch file, and so whoever eventually builds it starts from the right
hook points instead of re-deriving them.

**Source:** `_internal/dd.md`'s "First Visit Playthrough" — a two-day
narrative walkthrough of a new area, discovered via a Shop-style unlock,
built around discrete named places (Coral Gardens, Coral Castle and its
rooms, Coral Bridge, a Secret Coral Cave) and two fish (one exploring, one
settling in) accumulating shared memories. Its own stated design philosophy,
worth repeating verbatim since it's the thing that actually matters:

> Forest: "I want to explore." Coral Valley: "I want to stay."

Where the Forest is foraging + danger (Tiger Shark, a real risk while away),
Coral Valley is explicitly the opposite register — no predator, no risk,
just a place a bonded pair settles into. That contrast should stay load-
bearing in any real design, not get lost the moment implementation starts.

### Where things stand today

There is exactly **one** optional extra scene (the Forest), and the
mechanism that shows it is a hand-rolled two-way toggle, not a general
N-scene system: `_enter_forest()`/`_leave_forest()` (`aquarium.py:1524` and
`:1540`) just swap `app.widgets` between `aquarium_widgets` and `forest_widgets`
based on one `in_forest["value"]` boolean. `state["forest_unlocked"]` gates
a single Shop row (`FOREST_UNLOCK_PRICE`, `constants.py:925`) and a single
"Enter Forest" button. Notably, **cozy_tui already has a real, general
primitive for exactly this** — `app.screen(name)`/`app.show(name)`
(`cozy_tui/screen.py`) — and `aquarium.py` doesn't use it anywhere; the
Forest toggle predates it or just never got migrated. Adding a *second*
biome is the natural forcing function to stop hand-rolling this and move
onto `Screen`, rather than copy-pasting `in_forest`/`forest_widgets` a
second time as `in_coral_valley`/`coral_valley_widgets`.

Everything else the playthrough actually needs already exists as a real,
working mechanic elsewhere — Coral Valley mostly reads as **new content on
existing engine**, not new systems:

- **Memories** ("Visited Coral Valley for the first time," "Slept in the
  Coral Castle," "Watched Coral Valley from the Coral Bridge") are exactly
  `_log_memory()` (`aquarium.py:598`) — the same call already behind every
  Forest/dream/relationship memory line. No new logging mechanism needed,
  just new call sites and new strings.
- **One fish explores, the other relaxes** (Steve investigates the Castle
  while Kitty finds a quiet corner) is exactly the personality-weighted
  behavior split the Forest already has (`FOREST_EXPLORER_CHANCE_MULT` vs.
  a Shy/Lazy fish's own reduced eagerness, `_check_foraging()` at
  `aquarium.py:2422`, the weighting itself at `2456`) — this narrative would
  fall out for free from reusing that same weighting against Coral Valley's
  own travel roll, rather than needing bespoke scripting per personality.
- **A discrete room you can look inside** (a Coral Room, the Coral Garden
  Room) is closest to `_build_castle_interior()`
  (`termquarium/inspectors.py:342`) — a read-only, live-refreshing peek
  view reached by choice from an Inspector, not a real navigable space. It
  is the right *shape* of interaction (quiet, deliberate, opt-in), but the
  playthrough's rooms are chained together (Gardens → Castle → its rooms →
  Bridge → Secret Cave) in a way Castle Interior's single flat view isn't —
  see open question below.
- **"Found a favorite place"** already exists as `favorite_decoration`
  (`fish.py:204`, rolled once at birth) — Coral Valley introducing its own
  favorite *location* is either a second, Coral-Valley-scoped instance of
  that same idea, or (cleaner) a generalization of "favorite thing" that
  isn't hardcoded to a `Decoration`.
- **No danger system needed.** Deliberately: Coral Valley's whole point is
  the *absence* of a Tiger-Shark-style threat. `_check_forest_danger()`
  (`aquarium.py:3126`) should have no Coral Valley equivalent — resist the
  urge to give every biome a danger mechanic just because the Forest has
  one.

### Decisions

The four open questions above, now answered:

1. **Multi-room navigation: yes, a real nested structure**, not one flat
   scene. Three levels — the structural shape below is decided; the exact
   ASCII layouts are **not** (a quick illustrative sketch from the
   conversation this was designed in, not a mockup to build literally —
   the actual art is a later, separate decision):
   - **Coral Valley** — a top-level scene (the natural `Screen`, per above)
     drawn as a map with the Coral Castle as a clickable landmark leading
     into it.
   - **Coral Castle** — reached by clicking that landmark: a list of rooms,
     each with a small preview, "click to enter."
   - **Individual rooms** — reached from that list; closest existing
     precedent is still `_build_castle_interior()`'s occupancy view (beds,
     who's inside), one per room instead of one per container.
   
   This is a real Screen *stack* (Valley → Castle → room), not the
   Forest's single flat swap — the one piece of new navigation
   architecture this feature actually needs.
2. **Keen Explorer: eagerness decays with how long the area's been
   available, not a flat multiplier — done for the Forest.** Freshly
   unlocked → near-certain to explore ("as soon as possible",
   `KEEN_EXPLORER_FRESH_CHANCE`, decaying linearly over
   `KEEN_EXPLORER_URGENCY_DECAY_SECONDS`); long-available → settles to the
   same `KEEN_EXPLORER_FOREST_CHANCE_MULT` boost as before ("explore when
   not busy"). `forest_unlocked_at` tracks the unlock moment (persisted as
   elapsed seconds, same trick as `day_tick_remaining`, so a save/load
   doesn't reset the decay clock). Still Forest-specific by name — needs
   generalizing to "whichever optional area exists" once Coral Valley (or
   any second biome) is real.
3. **Unlock cost and gating: $980, and requires owning at least one
   Axolotl.** A real prerequisite beyond money, unlike the Forest's
   money-only `FOREST_UNLOCK_PRICE` — the Shop row would need an
   affordability *and* eligibility check.
4. **Yes — biome residency should survive Save/Load. Day/night phase and
   in-progress dreams now do too (done, ahead of Coral Valley itself).**
   Both were a real, pre-existing gap — neither `environment`/
   `session_start` nor `Fish.dream` was in `_snapshot()`/`_load_snapshot()`
   before this session, so a save/load round trip silently reset the world
   to midday with no one dreaming. Fixed via a persisted `day_fraction`
   (the same 0..1 value `_update_environment()` already computes, reapplied
   to `session_start` on load) and a fully self-contained per-fish `dream`
   field (not e.g. a variant title to re-look-up later, so it can't break
   if `DREAM_FRAMES` changes shape). Deliberately doesn't restore the
   nightmare-reaction sub-timers (`_nightmare_wake_at` and its siblings) --
   a reloaded nightmare just lingers peacefully instead of forcing its own
   early scared-awake wake. Coral Valley's own biome-residency persistence
   is still unbuilt (there's no biome to persist yet), but has this exact
   pattern to follow once it exists.

**Bonus, from the same conversation:** Coral Valley is Axolotls' favorite
place — they should be the species most likely to visit it, stay there
(a natural fit for `favorite_decoration`-style "favorite location" once
that generalizes, per the note above), and explore it once there.
