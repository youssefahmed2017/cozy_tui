# 🐠 TermQuarium

A cozy aquarium simulator that runs entirely in your terminal — built as a showcase/stress-test example for [cozy_tui](../../README.md). Every fish is its own independently-moving widget, decorations are real ASCII art, and the whole tank keeps living (day/night, hunger, friendships, sleep) whether you're clicking around or just watching.

```
  Money: $141   Food: 15   Fish: 6   🌙 Night, 21°C

  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                                                 <o
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

| Key | Action |
|---|---|
| Click open water | Drop a pinch of food |
| Click a fish or decoration | Inspect it |
| `S` | Open the Shop |
| `G` | Settings |
| `P` | Save |
| `L` | Load |
| `H` | Help |
| `Esc` | Pause |
| `Ctrl+C` | Return to the Main Menu (Resume, New Aquarium, Load, Settings, Help, Quit) |
| `Z` | Stress test — mass-spawn fish up to the cap (debug) |
| `` ` `` | Cheat Console — typed commands for testing (debug) |

## What's in the tank

- **Fish** — Goldfish, Angelfish, Betta, and the Shark (a predator that hunts other fish instead of food). Each one gets a personality — Friendly, Explorer, Shy, Greedy, Lazy, or Playful — that shapes its steering, and can independently also be **Sleepy**. A Sleepy fish genuinely stays asleep past the normal Night → Morning transition until a same-container Friend or Neutral tankmate wakes it (a Rival never bothers) — each attempt has a real chance to resist, but it's never permanently stuck: a randomized number of chances (fewer for a Friend than a Neutral acquaintance) guarantees it eventually wakes. Fish grow from Baby → Juvenile → Adult, get hungry, and can be sold from their Inspector panel.
- **Axolotl** — a fifth, non-predator resident, not just another fish reskinned: it rests far more than anything else in the tank (with its own closed-eyes look while doing it) and never schools, even with another Axolotl. Same price range, same growth, same everything else — the difference is personality, not power. It has its own favorite foods (Brine Shrimp, Bloodworms, Worms), which is where Treats come in.
- **Treats** — beyond bulk Fish Food (dropped in the water, eaten by whoever's nearest), the Shop also sells five named treats — Brine Shrimp, Worms, Bloodworms, Plankton, and Pizza — bought in packs and fed directly to one chosen fish from its own Inspector. Feeding a fish its favorite food (shown right there in the Inspector) earns a nicer toast, never a bigger stat — Pizza, meanwhile, is a single-serving indulgence every fish loves for no particular reason.
- **Decorations** — Plant, Driftwood, Rock, and Castle. Rock and Castle are *containers*: fish can claim one to sleep inside overnight (priority: favorite spot → a bonded tankmate's container → nearest one with room → the floor), disappearing from view until they wake. Click one to peek in, or click **Enter** for a quieter, dedicated interior view — beds, pillows, who's asleep versus lingering awake, and (if a Sleepy fish is being woken) a live *boop* — that keeps updating while it's open instead of a one-time snapshot. The whole room leaves together once everyone inside is awake, not one at a time.
- **Relationships** — every pair of fish quietly tracks a continuous bond score, nudged by real events (waking a friend up, sleeping together, giving up a home so someone else could have it) and slowly decaying if left alone. You never see the number — just a state (Rival/Dislikes/Neutral/Friend/Best Friend) and a short list of why, in each fish's Inspector. Bonds are earned, not rolled at birth.
- **Day/night cycle** — water temperature and the tank's background tint drift together over one continuous curve; Night puts non-hungry fish to sleep (a hard stop, not just slower). Mornings occasionally get a lighthearted vignette when a Friend pair wakes up together.
- **Economy** — a Shop for more fish/food/decorations, visitor donations that pay out (and toast) the moment they happen rather than waiting for the day to end, an Emergency Aquarium Welfare safety net for a totally bankrupt tank, and a Pause menu (`Esc`) that actually freezes the simulation, not just the screen.
- **Save/Load** — name a save once and `P` keeps saving into it; the Load menu can Rename, Duplicate, or Delete any save.
- **Cloud Saves** — optional: set up a Cloud Key from Settings to sync a named save to the cloud and restore it again on a different machine. No account/password — the key itself is the credential, so keep it somewhere safe.
- **Main Menu, anytime** — `Ctrl+C` pauses and returns to the Main Menu from anywhere (even from inside another menu), with a Resume button to pick your session back up exactly where it was, or New Aquarium/Load/Settings/Help/Quit if you'd rather not.
- **Achievements** — 11 account-wide milestones (a first friendship, a first baby, setting up Cloud Saves, ...) that survive a New Aquarium or a Load, since they're tied to the machine, not any one save. Always transparent — every name and description shows whether it's unlocked or not.
- **Random Events** — about once every 8 days, something happens on its own: a stray fish wanders in and stays for free, a storm rolls through (a real live event now — every awake fish heads for the nearest container and huddles there until it passes), a few dollars turn up in the gravel, or a fish does a little spin for no reason.
- **Dreams** — sleeping fish occasionally dream, shown as a 💭 next to their 😴 and clickable into a small looping animated scene. Personality leans which kind (Explorer → Fantasy, Greedy → Food, Shy → Home, Friendly → Friendship, Lazy/Playful → Happy) about 60% of the time; the rest is spread across the others. A fish's own memory shapes it further — a recent shark scare, a recent moment with its Friend, or a tankmate it's lost can all resurface in a dream. A nightmare is the one dream with real consequences: the fish wakes up scared after 5 seconds, then quietly relocates to sleep beside a Friend if it has one.
- **Fish Memory Log** — every fish keeps its own diary in its Inspector (up to 10 entries, oldest dropped first) — a favorite treat, waking a friend up, becoming friends or rivals, surviving a storm, a tankmate that isn't around anymore.
- **Cheat Console** — press `` ` `` for a small typed-command console meant for testing: `spawn_fish(species, name=None, amount=1)`, `set_health`/`set_hunger(fish_name, amount)`, `set_money`/`set_food(amount)`, and `buy(name)` (still costs money, like the real Shop). Commands are parsed structurally, never `eval()`'d, and every one calls the same real code the Shop/Inspector already use.

## Building a standalone Windows executable

The `TermQuarium.spec` (PyInstaller) and `TermQuarium.iss` (Inno Setup) files in this directory package the game as a double-clickable `.exe` and installer. Run both from inside `examples/aquarium/`:

```bash
pyinstaller TermQuarium.spec        # -> dist/TermQuarium.exe
iscc TermQuarium.iss                # -> Output/TermQuarium-Setup.exe (needs Inno Setup)
```

## Tests

The game's pure logic (steering, hunger, economy, relationships, save format) is unit-tested independently of any real terminal:

```bash
python -m pytest tests/test_aquarium.py tests/test_termquarium_save.py tests/test_termquarium_world.py tests/test_termquarium_cloud.py tests/test_termquarium_cloud_api.py tests/test_termquarium_console.py -q
```

## Project layout

```
aquarium.py              # main() only -- wires everything into one running App
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
  shop.py, ui.py, inspectors.py   # Shop, menus, and Inspector panel builders
```
