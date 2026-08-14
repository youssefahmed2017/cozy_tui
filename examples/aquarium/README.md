# 🐠 TermQuarium

A cozy aquarium simulator that runs entirely in your terminal — built as a showcase/stress-test example for [cozy_tui](../../README.md). Every fish is its own independently-moving widget, decorations are real ASCII art, and the whole tank keeps living (day/night, hunger, friendships, sleep) whether you're clicking around or just watching.

```
  Money: $141   Food: 15   Fish: 6   🌙 Night, 21°C

  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                                                  😴
        😴     😴                                 <o 😴
        o>    <o                                      o>
                                                                /^\ /^\
      )                                                        | | | |
     (            ___                                         _|_|_|_|_
      )   ~~~~~~ /   \                                        |       |
     ==   \____/ \___/                                        |_______|
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
```

## Running it

```bash
python examples/aquarium/aquarium.py
# or
cozy-tui run examples/aquarium/aquarium.py
```

No extra dependencies beyond `cozy_tui` itself.

## Controls

| Key                        | Action                                                                     |
|----------------------------|----------------------------------------------------------------------------|
| Click open water           | Drop a pinch of food                                                       |
| Click a fish or decoration | Inspect it                                                                 |
| `S`                        | Open the Shop                                                              |
| `G`                        | Settings                                                                   |
| `P`                        | Save                                                                       |
| `L`                        | Load                                                                       |
| `H`                        | Help                                                                       |
| `Esc`                      | Pause                                                                      |
| `Ctrl+C`                   | Return to the Main Menu (Resume, New Aquarium, Load, Settings, Help, Quit) |
| `Z`                        | Stress test — mass-spawn fish up to the cap (debug)                        |
| `` ` ``                    | Cheat Console — typed commands for testing (debug)                         |

## What's in the tank

- **Fish** — Goldfish, Angelfish, Betta, and the Shark (a predator that hunts other fish instead of food). Each one gets a personality — Friendly, Explorer, Shy, Greedy, Lazy, or Playful — that shapes its steering, and can independently also be **Sleepy**. A Sleepy fish genuinely stays asleep past the normal Night → Morning transition until a same-container Friend or Neutral tankmate wakes it (a Rival never bothers) — each attempt has a real chance to resist, but it's never permanently stuck: a randomized number of chances (fewer for a Friend than a Neutral acquaintance) guarantees it eventually wakes. Fish grow from Baby → Juvenile → Adult, get hungry, and can be sold from their Inspector panel.
- **Axolotl** — a fifth, non-predator resident, not just another fish reskinned: it rests far more than anything else in the tank (with its own closed-eyes look while doing it) and never schools, even with another Axolotl. Same price range, same growth, same everything else — the difference is personality, not power. It has its own favorite foods (Brine Shrimp, Bloodworms, Worms), which is where Treats come in.
- **Treats** — beyond bulk Fish Food (dropped in the water, eaten by whoever's nearest), the Shop also sells five named treats — Brine Shrimp, Worms, Bloodworms, Plankton, and Pizza — bought in packs and fed directly to one chosen fish from its own Inspector. Feeding a fish its favorite food (shown right there in the Inspector) earns a nicer toast, never a bigger stat — Pizza, meanwhile, is a single-serving indulgence every fish loves for no particular reason.
- **Decorations** — Plant, Driftwood, Rock, and Castle. Buying one from the Shop doesn't drop it at a random spot anymore: it hands you a ghost that follows your mouse along the tank floor until you click to place it (Esc cancels and refunds). Rock and Castle are *containers*: fish can claim one to sleep inside overnight (priority: favorite spot → a bonded tankmate's container → nearest one with room → the floor), disappearing from view until they wake. Click one to peek in, or click **Enter** for a quieter, dedicated interior view — beds, pillows, who's asleep versus lingering awake, and (if a Sleepy fish is being woken) a live *boop* — that keeps updating while it's open instead of a one-time snapshot. The whole room leaves together once everyone inside is awake, not one at a time.
- **Relationships** — every pair of fish quietly tracks a continuous bond score, nudged by real events (waking a friend up, sleeping together, giving up a home so someone else could have it) and slowly decaying if left alone. You never see the number — just a state (Rival/Dislikes/Neutral/Friend/Best Friend) and a short list of why, in each fish's Inspector. Bonds are earned, not rolled at birth.
- **Day/night cycle** — Morning, Afternoon, Evening, and Night, all read off one continuous water-temperature/tint curve; Night puts non-hungry fish to sleep (a hard stop, not just slower). As the water cools into Evening, fish increasingly (never all at once — the chance itself scales with how cold it's actually gotten) head over to a Warm Lamp if you've placed one — basking visibly nearby, any number at once — or else a nearby Rock or Castle to actually go inside and warm up, tucked away out of sight like a real overnight sleeper. 🥶 on the way, ☺️ once settled. Mornings occasionally get a lighthearted vignette when a Friend pair wakes up together.
- **Economy** — a Shop for more fish/food/decorations, visitor donations that pay out (and toast) the moment they happen rather than waiting for the day to end, an Emergency Aquarium Welfare safety net for a totally bankrupt tank, and a Pause menu (`Esc`) that actually freezes the simulation, not just the screen.
- **Named Recurring Visitors** — on top of the ordinary anonymous foot traffic, a real, individually-named visitor occasionally shows up, picks a favorite fish (weighted toward pricier/rarer ones), and remembers it. If they come back and that fish is genuinely still around, they donate generously and light up — and the fish gets its own memory line for it. If their favorite isn't there, they barely donate at all. Persists across saves.
- **Save/Load** — name a save once and `P` keeps saving into it; the Load menu can Rename, Duplicate, or Delete any save.
- **Cloud Saves** — optional: set up a Cloud Key from Settings to sync a named save to the cloud and restore it again on a different machine. No account/password — the key itself is the credential, so keep it somewhere safe.
- **Main Menu, anytime** — `Ctrl+C` pauses and returns to the Main Menu from anywhere (even from inside another menu), with a Resume button to pick your session back up exactly where it was, or New Aquarium/Load/Settings/Help/Quit if you'd rather not.
- **Achievements** — 11 account-wide milestones (a first friendship, a first baby, setting up Cloud Saves, ...) that survive a New Aquarium or a Load, since they're tied to the machine, not any one save. Always transparent — every name and description shows whether it's unlocked or not.
- **Random Events** — about once every 8 days, something happens on its own: a stray fish wanders in and stays for free, a storm rolls through (a real live event now — every awake fish heads for the nearest container and huddles there until it passes), a few dollars turn up in the gravel, or a fish does a little spin for no reason.
- **Dreams** — sleeping fish occasionally dream, shown as a 💭 next to their 😴 and clickable into a small looping animated scene. Personality leans which kind (Explorer → Fantasy, Greedy → Food, Shy → Home, Friendly → Friendship, Lazy/Playful → Happy) about 60% of the time; the rest is spread across the others. A fish's own memory shapes it further — a recent shark scare, a recent moment with its Friend, or a tankmate it's lost can all resurface in a dream. A nightmare is the one dream with real consequences: the fish wakes up scared after 5 seconds, then quietly relocates to sleep beside a Friend if it has one.
- **Fish Memory Log** — every fish keeps its own diary in its Inspector (up to 10 entries, oldest dropped first) — a favorite treat, waking a friend up, meeting a tankmate for the first time, becoming friends or rivals, surviving a storm, growing into a Juvenile, a tankmate that isn't around anymore. A baby genuinely sleeping — or swimming — beside its own real parent gets its own line for it, its very first time settling at its favorite spot gets a baby-voiced "the {Decoration} is really big" instead of the ordinary line, a wandering baby that drifts over to a real ambient bubble and catches it gets "I chased a bubble today," and two babies that happen to swim close together occasionally spontaneously race (a cosmetic 💨 burst of speed, not an actual destination) and both get "X challenged me to a race." A handful of moments are too important to ever scroll off, and stay pinned as **Lifelong Memories** instead: being born, growing into an Adult, having a child, a first Best Friend, making it home from a Lost Adventure. Long-lived fish also occasionally **reflect** on how long they've been around (one year, and beyond) — pure flavor, no gameplay effect.
- **Cheat Console** — press `` ` `` for a small typed-command console meant for testing: `spawn_fish(species, name=None, amount=1)`, `set_health`/`set_hunger(fish_name, amount)`, `set_money`/`set_food(amount)`, `buy(name)` (still costs money, like the real Shop), `set_time(phase)`, `spawn(item, amount=1)` (a free special food like "Pizza"), `give_nightmare`/`give_dream(fish_name, ...)`, `find_legendary(species_name=None)`, `grant_trait(fish_name, trait)`, `advance_day(amount=1)`, `start_lost_adventure`/`advance_adventure_day(fish_name, ...)`, `set_happiness`/`set_speed`/`set_personality(fish_name, ...)`, `force_relationship(fish_a, fish_b, score)`, `set_day(amount)`, `toggle_forest(unlocked)`, `spawn_decoration(kind)`, `remove_fish(fish_name)`, `force_random_event(event)`, and `run(code)` (a sandboxed Python snippet, via `RestrictedPython`, for anything a single command call can't express). Type `help` for the full list. Commands are parsed structurally, never `eval()`'d, and every one calls the same real code the Shop/Inspector already use.

## Building a standalone Windows executable

The `TermQuarium.spec` (PyInstaller) and `TermQuarium.iss` (Inno Setup) files in this directory package the game as a double-clickable `.exe` and installer. Run both from inside `examples/aquarium/`:

```bash
pyinstaller TermQuarium.spec        # -> dist/TermQuarium.exe
pyinstaller update.spec             # -> dist/update.exe (the updating launcher)
iscc TermQuarium.iss                # -> Output/TermQuarium-Setup.exe (needs Inno Setup)
```

## Auto-updates

The installed shortcuts launch `update.exe`, not `TermQuarium.exe` directly. On
each run it applies any update staged on a previous launch (a fast local swap —
you can't overwrite a running exe on Windows, which is exactly why the launcher
is separate), starts the game, and — at most once a day, in a detached
background process — checks `termquarium.vercel.app/version.json` and downloads
any newer build to stage for next time. Every failure (offline, bad download,
checksum mismatch) falls through to launching the installed build, so the
updater can never stop you from playing. `update.py --skip` bypasses the check.

The install is per-user (`PrivilegesRequired=lowest`) so staging a new build
never needs an admin/UAC prompt. All the decision logic lives in
`termquarium/updater.py` (pure standard library, unit-tested in
`tests/test_termquarium_updater.py`); `update.py` is just the glue.

**Cutting a release:**

1. Bump `GAME_VERSION` in `termquarium/constants.py` and `MyAppVersion` in
   `TermQuarium.iss` to the new version.
2. Build `dist/TermQuarium.exe` and `dist/update.exe` (above), and the
   installer.
3. Upload the new `TermQuarium.exe` to the release URL, compute its SHA-256
   (`sha256sum dist/TermQuarium.exe`), and update `website/version.json`'s
   `version`, `url`, and `sha256`. Deploying the site publishes the manifest;
   installed clients pick it up within a day.

## Tests

The game's pure logic (steering, hunger, economy, relationships, save format) is unit-tested independently of any real terminal:

```bash
python -m pytest tests/test_aquarium.py tests/test_termquarium_save.py tests/test_termquarium_world.py tests/test_termquarium_cloud.py tests/test_termquarium_cloud_api.py tests/test_termquarium_console.py tests/test_termquarium_updater.py -q
```

## Project layout

```
aquarium.py              # main() only -- wires everything into one running App
update.py                # the updating launcher the installed shortcut runs
termquarium/
  constants.py           # every tuning constant, species/decoration catalogs
  steering.py            # pure movement math (steer, avoid, school, ...)
  economy.py             # hunger, feeding, attractiveness, visitor income
  relationships.py       # personality, Sleepy, the relationship-score system
  fish.py                # the Fish widget + its steering/sleep/home logic
  tank_objects.py        # Food, Decoration
  bubbles.py             # ambient bubble particles
  vignettes.py           # the morning "*boop*" in-tank caption
  world.py               # day/night cycle, water temperature
  save.py                # versioned JSON save/load
  dreams.py              # the Dream System: categories, memory-linking, the animation widget
  console.py             # the Cheat Console: command parser, registry, the widget
  updater.py             # self-update logic for update.exe (version compare, staging, applying)
  shop.py, ui.py, inspectors.py   # Shop, menus, and Inspector panel builders
```
