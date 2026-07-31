# 🐟 Update 1 — More Fish



This is where the fun begins.



I wouldn't make every fish unique.



I'd make each one have:



* sprite

* price

* rarity

* favorite treats

* maybe one small quirk



Just like Axolotl.



---



# Common



Cheap.



Beginner fish.



```text

Goldfish

Salmon

Anchovy

Sardine

```



---



# Uncommon



```text

Betta



Angelfish

Axolotl


```



---



# Rare



```text



Discus



Arowana

Octopus


Seahorse

```



---



# Predators



```text

Shark

```



---



# Legendary



These should be



VERY



rare.



```text

Golden Axolotl



Ghost Fish



Crystal Fish



Lunar Betta

```



No stat bonuses.



Just



> "YOU FOUND ONE??"



---



# Small personality quirks



Instead of



20 mechanics.



Examples:



---


### Salmon



Moves constantly.



---



---



### Seahorse



Slow.



Always upright.



---



### Octopus



Sometimes changes color.



---



Again...



Flavor.



Not optimization.



---



# Shop



Eventually



```text

Today's Stock



Goldfish



Cod



Bass



Betta



Out of Stock:

Axolotl



Out of Stock:

Shark

```



Refreshes daily.



---



# 🎣 Update 2 — Fishing



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



🦀 Crab (I guess he's a secret shop item that can't be bought unless you go fishing. So he could stay in your aquarium)



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

Caught



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



## Shop integration


```text

Fish Shop



Goldfish



Betta



Cod



Out of Stock



Axolotl



Shark

```



Need them?



Go fishing.



---



## Rare Events



While fishing:



```text

✨ Treasure Chest: Can contain money, fish, or wood



🪙 Old Coin: simply can be sold



📜 Message in a Bottle: click to open and read a message.



🐚 Giant Shell: can be sold FOR A LOT OF MONEY



🦑 Kraken Shadow: I don't really know why it's useful. We can just pretend it's a legendary thing



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



❤️ Finn became friends with Bubbles.



🌅 Morning vignette:

Bubbles showed Finn the Castle.

```



That's the kind of thing that makes players think, *"I remember catching **that** fish."* The fishing trip becomes the beginning of that fish's story, not the end of a loot roll.

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
│
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

"Put shark in tank"

Because sharks need:

* huge space
* special walls
* different food

Example:

```
Shark Exhibit

Capacity:
5 sharks

Requirements:
✓ Large Tank
✓ Reinforced Glass
✓ Ocean Filter
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
500 coins

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

# Phase 9 — Staff System (Later)

Don't add this immediately.

Future update:

Hire:

```
👨‍🔬 Scientist
- discovers fish information

🧹 Cleaner
- reduces maintenance

👩‍🏫 Guide
- increases visitors
```

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

* staff
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

# Visitor Expansion Playthrough
**Day 1 — First visit:**
```
🎫 New Visitor!

Maya arrived.

*Maya watches the tank*
*Steve swims by*
*Maya watches Steve for a while*
*Kitty swims by*
*Maya watches Steve again*

Maya left.
💰 Maya donated $5.
```

---

**Day 4:**
```
🎫 Returning Visitor! (Visit #2)

Maya is back.

*immediately looks for Steve*
*Steve is sleeping*

💬 "oh... he's asleep"

Maya watched Kitty instead.
Maya left early.
💰 Maya donated $2.
```

---

**Day 5 — Steve wakes up:**
```
Morning:

Steve's memory:
"I slept longer than usual."

Meanwhile:

🎫 Returning Visitor! (Visit #3)

Maya arrived.

*Steve is awake*
*Maya visibly stays longer*

💬 "there he is 🥺"

Maya stayed for 2 hours.
💰 Maya donated $15.

Maya's favorite fish:
🐟 Steve
```

---

**Day 10 — Steve goes to Coral Valley:**
```
🎣 Steve is exploring...

🎫 Returning Visitor! (Visit #4)

Maya arrived.

*looks for Steve*
*Steve isn't there*

💬 "..."

Maya looked at every corner of the tank.

💬 "where did he go"

Maya left after 10 minutes.
No donation. 💀
```

---

**Day 12 — Steve returns:**
```
🌅 Morning

Steve returned from his adventure.
Steve's memory:
"I missed the tank.
I missed everyone."

🎫 Returning Visitor! (Visit #5)

Maya arrived.

*sees Steve immediately*

💬 "HE'S BACK"

Maya stayed for 4 hours.
💰 Maya donated $50.

Steve's memory:
"Someone seemed really relieved to see me.
I wonder if I was missed."

🥺🥺🥺💀
```

---

**Day 30 — Maya's milestone:**
```
🎫 Returning Visitor! (Visit #10)

Maya is back.

💬 "I've been coming here for a month.
    Steve always makes my day better."

💰 Maya donated $100.
🏆 Maya is now a Regular Visitor.

Steve's memory:
"I recognized someone today.
They always seem happy when they see me.
I think I make them happy.
I like that."

😭😭😭😭💀
```

---

**Day 50 — The note:**
```
🎫 Returning Visitor! (Visit #15)

Maya arrived.

Maya left a note:

📝 "To whoever takes care of this aquarium —
    Steve has been my favorite part of my week
    for 50 days now.
    Thank you for keeping him happy.
    — Maya"

💰 Maya donated $200.

Player:
😭😭😭😭😭
```

---

**The stats screen:**
```
╔══════════════════════════════╗
║      Most Loved Fish         ║
╠══════════════════════════════╣
║ 🥇 Steve      — 47 fans      ║
║ 🥈 Kitty      — 23 fans      ║
║ 🥉 Finn       — 8 fans       ║
╚══════════════════════════════╝
```

Steve is not surprised 😂😎

---

The beautiful part? 👀

Maya never met Steve 💀
Steve never met Maya 😭
But Steve made her week better for 50 days

And Steve's only memory of her is:

```
"I think I make them happy.
I like that."

```
🥺🥺

---

# MEMORIES UPDATED

# 🐠 Stage 1 — Birth Memories

Every fish starts with a handful of innocent memories.

```text
[Day 1]
I was born.

[Day 3]
Mom stayed beside me while I slept.

[Day 5]
I discovered that my fins belong to me.
I moved them for the first time.

[Day 8]
Dad helped me swim today.

[Day 11]
I slept next to Mom and Dad.
```

These happen automatically as the fish grows.

---

# 🌱 Stage 2 — Childhood

The fish begins discovering its world.

```text
[Day 18]
I chased a bubble today.

[Day 21]
I found a shiny shell.

[Day 26]
I met Steve today.
He seems nice.

[Day 30]
I got lost for a little while.
Mom found me.
```

Simple, curious memories.

---

# 🐠 Stage 3 — Growing Up

Now the fish starts making its own experiences.

```text
[Day 72]
Bob challenged me to a race.

[Day 83]
I caught my first shrimp by myself.

[Day 90]
I explored the Forest.
```

---

# ❤️ Stage 4 — Relationships

Relationships begin shaping the fish's personality.

```text
[Day 140]
Kitty became my best friend.

[Day 167]
Steve looked sad today.

[Day 182]
Bubbles shared some shrimp with me.

[Day 190]
We watched the sunset together.
```

---

# 🌍 Stage 5 — Adventures

The biggest moments of the fish's life.

```text
[Day 280]
I visited Coral Valley.

[Day 350]
I got lost during an adventure.

[Day 366]
I slept inside the Tree House.

[Day 401]
I discovered a hidden cave.
```

---

# 🧠 Active Memories

Each fish only keeps a limited number of **active memories** (for example, 40–60).

These affect behavior:

* Friends
* Best friends
* Favorite places
* Fears
* Recent adventures
* Things they recently learned

Older memories gradually leave active memory as new experiences replace them.

---

# 📖 Full History

Nothing is ever deleted.

The player can always open:

```text
═══════════════════
Steve's Full History
═══════════════════
```

and scroll from:

```text
[Day 1]
I was born.
```

all the way to:

```text
[Day 1024]
Today I visited Coral Valley with Kitty.
```

It's the fish's complete autobiography.

---

# ⭐ Lifelong Memories

Some memories are too important to ever leave active memory.

Examples:

* Birth
* Becoming Best Friends
* First Adventure
* First Child
* Death of a Best Friend
* Player Adoption
* First Visit to Coral Valley

---

# 📅 Reflection Memories

Occasionally, fish can reflect on their lives.

```text
[Day 365]
I've been alive for one whole year.
```

```text
[Day 700]
I know this aquarium feels like home.
```

```text
[Day 1000]
I've met so many wonderful fish.
```

These don't change gameplay—they simply make older fish feel like they've lived a long life.

---

# 👶 Baby Personality

Babies shouldn't think like adults.

Their memories should be tiny discoveries.

```text
[Day 4]
I made lots of bubbles today.
```

```text
[Day 6]
Dad is really fast.
```

```text
[Day 7]
I like sleeping next to Mom.
```

```text
[Day 10]
The big rock is really big.
```

🥺


