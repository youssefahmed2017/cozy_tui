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

`App.run()` (`cozy_tui/app.py:2264-2420`) is a single-threaded loop that
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

**Status: all six traits shipped.** `Fish.traits`, `relationships.grant_trait()`,
save/load compatibility, the Cheat Console's `grant_trait()` command, and the
Inspector display (steps 1/2/4/5 below) are all in place for **Food Lover**,
**Dreamer**, **Fast Swimmer**, **Energetic**, **Mischievous**, and **Keen
Explorer** (each with a real, existing-event growth trigger — see
`CHANGELOG.md`). **Not yet done:** combination flavor text (step 3) — no
trait's mechanical effect depends on which others are also present, only
which individual tags exist; a later pass could add cosmetic text for
specific pairs (e.g. Dreamer + Keen Explorer) the way `updates.md` originally
pitched it.

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
(`termquarium/constants.py:101`) is a fixed tuple; `random_personality()`
(`termquarium/relationships.py:43-45`) rolls exactly **one**, uniformly, once
at birth, stored as a plain `self.personality: str`
(`termquarium/fish.py:176`). It's then read via `self.personality == "X"`
scattered across **~28 call sites** in `fish.py`, `relationships.py`, and
`aquarium.py` (steering priority, `_claim_home()`'s container-choice
reordering, wake-up score, forage chance/opt-out, food-seeking speed, …), and
persisted as that same plain string in every save
(`"personality": f.personality`, `aquarium.py:1021`). `tests/test_aquarium.py`
references `.personality` **81 times**. Any change here has to keep old saves
loading and not force a rewrite of that whole test surface just to add one
new trait.

**A stackable trait already exists, and is the template to generalize:**
`Sleepy` (`roll_is_sleepy()`, `termquarium/relationships.py:48-53`) is already
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
   backfilled the same way in `_load_snapshot`, `aquarium.py:1098-1102`).
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
