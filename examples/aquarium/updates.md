# 🎣 Update 1 — Fishing

This is where everything comes together.

---

## Fishing spots
```text
🌊 Pond
🌊 River
🌊 Lake
🌊 Ocean
🌊 Coral Reef
🌊 Deep Sea
```
Each has
different fish.

---

## Cast
```text
Press Space

↓

Cast

↓

Waiting...

↓

Nibble

↓

Catch!
```
Not twitchy.

Relaxing.

---

## Rewards

Possible catches

```text

🐟 Fish
🪵 Driftwood
💰 Coins
🪙 Treasure
🐚 Seashell
📜 Bottle
🦀 Crab (I guess he's a secret shop item that can't be bought unless you go fishing. So he could stay in your aquarium: <\_(°°)_/>
🦐 Shrimp
```

---

## Fish rarity
```text
Common
Uncommon
Rare
Legendary
```
---

## Weather (future)

Rain

↓

More Salmon



Night

↓

Catfish



Morning

↓

Carp

---

## Seasons (far future)
```text
Spring
Summer
Autumn
Winter
```

Changes available fish.

---

## Fishing Journal
```text
Caught:
✓ Goldfish
✓ Cod
✓ Salmon
✓ Betta
□ Whale
□ Ghost Fish
```

---

## Aquarium integration

When caught

```text
Keep

Sell

Release
```

---

If kept

Fish remembers

```text
"I came from the Ocean."
```

Could even influence dreams.

---

## Rare Events

While fishing:

```text

✨ Treasure Chest: Can contain money, fish, or wood
🪙 Old Coin: simply can be sold
📜 Message in a Bottle: click to open and read a message.
🐚 Giant Shell: can be sold FOR A LOT OF MONEY
👢 Old Boot 😂: Also can be sold
```

---

## Biome progression
```text
Start

↓

Pond

↓

River

↓

Lake

↓

Ocean

↓

Coral Reef

↓

Deep Sea
```

Each unlock costs money.

The same architecture as the forest: Can be unlocked in the shop, and works as a separate place

---

## One thing I'd add that fits **TermQuarium's** identity

Since wer fish already have **memories, dreams, personalities, and relationships**, I'd make catching a fish feel like introducing a **new resident**, not collecting an item.

Imagine this sequence:

```text
🎣 You caught a Salmon!

Name it?

> Finn

🐟 Finn cautiously enters the aquarium...

💬 "The other fish seem curious."
```



A few in-game days later:

```text
💭 Finn dreamed about the river he came from.
❤️ Finn became friends with Alex.

🌅 Morning vignette:
Alex showed Finn the Castle.
```
That's the kind of thing that makes players think, *"I remember catching **that** fish"*.

The fishing trip becomes the beginning of that fish's story, not the end of a loot roll.

---

# 🏗 TermQuarium Expansion Update Plan

## Phase 1 — Multi-Tank System (Foundation)

### Goal:

Allow the player to own multiple tanks.

Current:

```text
Aquarium
 └── Main Tank
```

New:

```text
Aquarium
├── Main Tank
├── Coral Reef Tank
├── Deep Sea Tank
└── Shark Exhibit
```

---

## New Data Structure

Something like:

```python
class Aquarium:
    tanks: list[Tank]
    current_tank: Tank
```

Each tank:

```python
class Tank:
    name: str
    fish: list[Fish]
    decorations: list[Decoration]
    size: int
    type: TankType
```

Example:

```python
Tank(
    name="Main Tank",
    size=100,
    type="freshwater"
)
```

---

# Phase 2 — Tank Navigation

Add a new UI:

```
=== Aquarium Map ===

🐟 Main Tank
   Steve, Kitty

🌊 Deep Sea
   Empty

🦈 Shark Zone
   Locked

[Enter]
[Upgrade]
[Back]
```

Player can move between locations.

---

# Phase 3 — Tank Types

Different tanks should have different purposes.

---

## 🐠 Freshwater Tank

Starter tank.

Contains:

* goldfish
* shrimp
* normal fish

Features:

* easiest maintenance
* beginner area

---

## 🌊 Deep Sea Tank

Unlocked later.

Contains:

* rare fish
* glowing creatures
* mysterious species

Requirements:

* higher cost (1000$. Which also means we might want to expand the money system)

Possible events:

```
A strange creature appeared...
```

---

## 🦈 Shark Exhibit

BIG milestone.

Not just:

* "Put shark in tank"

Because sharks need:

* lot of space
* different food

Example:

```
Shark Exhibit

Capacity:
5 sharks

Requirements:
✓ Large Tank
✓ Crabs
```

---

## 🪸 Coral Reef Exhibit

A beautiful peaceful tank.

Contains:

* tropical fish
* coral
* small creatures

Bonus:

Fish happiness increases.

---

# Phase 4 — Tank Expansion

Every tank can grow.

Example:

## Level 1

```
Small Tank

Capacity:
7 fish
```

## Level 2

```
Medium Tank

Capacity:
15 fish

+ decorations
```

## Level 3

```
Large Exhibit

Capacity:
50 fish

+ rare species
```

---

Upgrade screen:

```
Main Tank

Size:
████░░ 60%

Fish:
8/10

Upgrade cost:
300$

[Upgrade]
```

---

# Phase 5 — Exhibits / Cages

This is the coolest part.

A tank can contain sections.

Example:

```
Main Aquarium

├── Normal Area
│   └── Steve + friends
│
├── Cave Area
│   └── Special fish
│
└── Predator Area
    └── Shark
```

Basically:

Tank
→ Exhibits
→ Fish

---

# Phase 6 — Tank Relationships

BRO this fits your existing systems.

Fish shouldn't just know fish.

They know places.

Example:

Steve:

```
Memories:

Day 1:
Arrived at Main Tank

Day 50:
Moved to Coral Reef

Day 100:
Visited Deep Sea
```

---

A fish could have:

Favorite Tank:

```
Steve loves:
🪸 Coral Reef
```

Reason:

```
"Steve enjoys calm places."
```

---

# Phase 7 — Tank Events

Different tanks get different events.

---

## Main Tank

Normal events:

```
Visitors increased today!
```

---

## Deep Sea

Mystery events:

```
Something moved in the darkness...
```

---

## Shark Exhibit

Danger events:

```
The shark damaged equipment!
```

---

## Coral Reef

Beautiful events:

```
The coral started glowing!
```

---

# Phase 8 — Aquarium Visitors

Expansion makes visitors much more interesting.

Visitors now have preferences.

Example:

```
Visitor:

Alex

Favorite Exhibit:
Deep Sea

Favorite Fish:
Steve
```

A visitor might say:

```
"I came back because Steve is still here!"
```

🥺

---

# Phase 10 — Aquarium Map

Eventually:

```
             Aquarium

                ⭐

      ┌─────────┼─────────┐

      🐟        🌊        🦈
   Main      Deep Sea   Shark

                |

              🪸
           Coral Reef
```

---

# Implementation Order

I would NOT build everything at once.

Do:

## Update 1

✅ Tank class
✅ Multiple tanks
✅ Navigation

---

## Update 2

✅ Tank upgrades
✅ Capacity system
✅ Buying new tanks

---

## Update 3

✅ Exhibits
✅ Special tank types

---

## Update 4

✅ Tank-specific events
✅ Visitor interactions

---

## Update 5

✅ Advanced systems

* aquarium map
* rare discoveries

---

BRO the biggest thing:

Do **not** make the new tanks just containers.

Make them places with history.

Because TermQuarium's strongest feature is not:

> "I have 100 fish."

It's:

> "Steve lived in the Main Tank for 50 days, then moved to the Coral Reef, and he still remembers his old home."

That's the kind of thing that makes a virtual world feel alive. 🥺🐟




