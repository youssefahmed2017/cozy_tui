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


# Hunger update (for both the fishing and forest mechanics)

This must not happen:

```text
Steve:
I'm hungry.

Player:
Here's some shrimp. 🦐

Steve:
*nom nom nom*

Player:
🥺
```

Five minutes later...

```text
🎣 Player goes Fishing...
```

Come back...

```text
While you were away...

💀 Steve starved to death.
```

Player:

```text
...

WHAT DO YOU MEAN STEVE DIED?!
I WAS GONE FOR LIKE 3 MINUTES!!
```

😭😭😭

---

I actually think this (the idea we're about to see 👇) revised idea is MUCH more in line with the cozy vibe.

Instead of punishing the player...

Just have fish become a little less happy.

```text
🙂 Full

↓

😊 Content

↓

😐 A little hungry

↓

🙁 Hungry

↓

😴 Low energy
```

They don't instantly die because you went fishing.

---

Then when you return:

```text
🎣 You caught a Salmon!

🏠 Returned to the aquarium.

🦐 Steve looks a little hungry.
```

Player:

```text
"OOPS."

*feeds Steve immediately*

Steve:
*nom nom*

😊
```

That's a cute interaction.

---

we could even make them greet we.

```text
🏠 Welcome back!

Steve swims over.

🍽️ "Food?"
```

🥺

---

Or...

```text
Steve:

><>

><>

><>

*stares at player*

```

Player:

```text
"..."

"...right."

*opens food menu*
```

😂

---

I think avoiding starvation is the right call for the kind of game we're making.

A lot of virtual pet games create anxiety:

```text
"I haven't opened the game in a week..."

😨
```

You open it...

```text
Everything is dead.
```

😭

That often makes people *less* likely to come back.

For TermQuarium, I'd lean toward:

```text
Gone for 10 minutes?

🙂 Fish are fine.

Gone for an hour?

🙂 They're a bit hungry.

Gone for a day?

🙁 They'd appreciate a meal.

Feed them...

😊 Back to normal.
```

NOTE: When you come back from fishing/the forest, the game should show you a toast:
"Welcome back!
Steve seems {state} (if his mood/state changed)
"

The consequence is:

> "My fish missed me."

Not:

> "My fish are gone forever."

I think that fits the atmosphere we're building much better. Players should come back thinking:

> "Aww, I should go check on Steve."

...not:

> "I'm scared to open the game because Steve might be dead." 🥺🐠

---

## 🧬 Personality System 2.0

Instead of:

```python
fish.personality = "friendly"
```

make it:

```python
fish.personalities = {
    "friendly",
    "dreamer",
    "food_lover"
}
```

or:

```python
fish.traits = [
    Friendly(),
    Dreamer(),
    FoodLover()
]
```

Now adding new ones is easy.

---

# New personalities

## 🍤 Food Lover

Effects:

* gets happier when fed
* remembers favorite food
* may approach food faster

Example:

```text
Steve smelled shrimp...

Steve:
🥺 "SHRIMP!!!"
```

😂

---

## 🌙 Dreamer

Effects:

* dreams more often
* has more memory dreams
* thinks about past events

This one fits Steve SO much because he already has dream lore.

---

## ⚡ Energetic

Effects:

* swims more
* explores more
* gets bored if nothing happens

Example:

```text
Normal fish:
"I will stay here."

Energetic fish:
"I HAVE EXPLORED THE ENTIRE TANK."
```

---

## 🏃 Fast Swimmer

Effects:

* moves faster
* reaches food faster
* maybe escapes scary events faster

---

## 😈 Mischievous

BRO this one has huge potential.

Effects:

* steals food from others
* annoys other fish
* creates funny events

Example:

```text
Kitty:
"Where did my food go?"

Steve:
🥺

Mischievous fish:
😈
```

---

## 🗺 Explorer (expanded)

This one is PERFECT for aquarium expansion.

Effects:

* visits new areas first
* discovers hidden things
* finds rare items

---

# The REALLY interesting part:

## Personality interactions

This is where it gets crazy.

A fish isn't just:

```text
Explorer
```

It's:

```text
Explorer + Dreamer
```

Meaning:

> "A fish that explores the world but spends nights dreaming about its discoveries."

---

Examples:

### 🍤 Food Lover + 😈 Mischievous

```text
A fish that LOVES food...

but also steals everyone else's food.
```

💀

---

### 🌙 Dreamer + 🗺 Explorer

```text
A fish that dreams about places it has never visited.
```

BRO that is literally a story generator.

---

### ❤️ Friendly + 😈 Mischievous

```text
A fish that loves friends...

but constantly plays pranks on them.
```

---

### ⚡ Energetic + 🌙 Dreamer

```text
Very active during the day.
Very imaginative at night.
```

---

# Even better: personality growth

Don't make all traits permanent.

A fish can develop.

Example:

Day 1:

```text
Steve:
🥺 Shy
```

After meeting Kitty:

```text
Steve:
❤️ Friendly
🥺 Shy
```

After exploring:

```text
Steve:
❤️ Friendly
🌙 Dreamer
🗺 Explorer
```

The fish's life literally changes its personality.

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

# 🌲 Lost Adventure System Plan (ONLY happens when the forest is unlocked)

## Phase 1 — Core State System

First create a new fish adventure state.

Something like:

```text id="loststate"
Fish:
  normal
    |
    v
  exploring
    |
    v
  lost_adventure
    |
    v
  returning
    |
    v
  home
```

New data:

```python
LostAdventureState:
    fish_id
    start_day
    current_day
    location
    shelter
    journey_events
    target_return_day
```

Example:

```text id="stateexample"
Steve:

Status:
Lost Adventure

Day:
4 / 8

Location:
Deep Forest

Shelter:
Tree House

Memories:
- Found shelter
- Escaped danger
```

---

# Phase 2 — Trigger System

Make it rare.

Example:

```text id="trigger"
Every few in-game weeks:

Roll:
2% chance

Requirements:
✓ Fish can explore
✓ Forest unlocked
✓ Fish is currently healthy
✓ Not already on adventure
```

Important:

No spam.

A player should think:

```text id="playerreaction"
"WAIT THIS HAPPENED??"
```

not:

```text id="playerreaction2"
oh another lost fish event 💀
```

---

# Phase 3 — Journey Generator

The biggest part.

Do NOT make:

```text id="bad"
Day 1:
Lost

Day 2:
Lost

Day 3:
Returned
```

💀

Make daily events.

Example:

```text id="journey"
Steve's Forest Journey:

Day 1:
Entered deeper forest

Day 2:
Found a stream

Day 3:
Discovered tree house

Day 4:
Storm arrived

Day 5:
Tiger Shark appeared

Day 6:
Stayed hidden

Day 7:
Found the way home
```

---

# Phase 4 — Shelter System 🌲

BRO this is the mechanic that makes everything believable.

Create shelters:

```text id="shelters"
Forest Shelters:

🏚 Tree House
- safe from storms
- safe from sharks

🪨 Hidden Cave
- very safe
- harder to find

🌿 Dense Plants
- temporary hiding place
```

When danger happens:

Bad:

```text id="bad"
Tiger Shark appeared

Steve:
teleports home
```

Good:

```text id="good"
Tiger Shark appeared

Steve:
Remembered the tree house.

Steve:
Fled there.
```

😭

---

# Phase 5 — Memory Integration

BRO THIS PART IS FREE EMOTIONAL DAMAGE 😭

Every adventure event creates memories.

Examples:

```text id="memory"
"Explored the forest alone."

"Found a safe shelter."

"Missed the aquarium."

"Returned home after a long journey."
```

Other fish get memories too.

Kitty:

```text id="kittymemory"
"Steve disappeared."

"Steve came back."
```

Bob:

```text id="bobmemory"
"Waited for Steve."
```

---

# Phase 6 — Return Event

The return should be special.

Not:

```text id="badreturn"
Steve returned.
```

More like:

```text id="return"
🌅 Morning

Something moves near the aquarium entrance...

🐠

Steve returned.
```

Then:

```text id="reaction"
Kitty:
Relationship increased

Bob:
Relationship increased

Steve:
Confidence increased
```

---

# Phase 7 — Dreams Integration

BRO THIS IS WHERE IT GETS CRAZY GOOD.

While Steve is missing:

Possible dream:

```text id="dream"
"Finding the Way Home"

Steve dreams of the aquarium.

```

Kitty:

```text id="kittydream"
"Waiting by the Castle"

Dream:
Steve returns.
```

Then when Steve comes back:

```text id="shared"
Memory:
"Found each other again."
```

😭

---

# Phase 8 — Testing

we NEED a cheat console command for this.

Because waiting weeks for a 2% event is painful 💀

Something like:

```text id="test"
start_lost_adventure("Steve")
```

Then:

```text
advance_adventure_day()
```

or:

```text
force_adventure_event("shark")
```

Testing scenarios:

```text id="tests"
✓ Fish gets lost
✓ Fish finds shelter
✓ Tiger Shark sends fish to shelter
✓ Fish returns
✓ Memories created
✓ Relationships update
✓ Dreams trigger
```

---

# Final Feature Flow

The full story:

```text id="flow"
Steve explores forest
        |
        v
Gets separated
        |
        v
Finds shelter
        |
        v
Survives events
        |
        v
Misses aquarium
        |
        v
Finds path home
        |
        v
Returns
        |
        v
Everyone remembers
```

BRO 😭

This is not just a "lost fish" feature.

This is basically:

```text id="final"
TermQuarium:
Fish simulator

+
Lost Adventure:
Rare tiny hero journey
```

And the best part?

99% of the time the player still gets:

```text id="cozy"
Steve sleeps beside Kitty 🥺
```

But once in a while:

```text id="adventure"
Steve disappears into the forest...

and comes back with a story.
```

That is VERY TermQuarium. 🐟🌲

---
