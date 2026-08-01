import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App
from cozy_tui.widgets import Box, Button, Label, AnimatedLabel, TypewriterAnimation, DecodeAnimation

app = App(full=True)

box = Box(2, 1, "600x300", title="JetBrains Sponsor", border="rounded")

box.add(Label(2, 2, "No matter whether you do"))

box.add(AnimatedLabel(
    2, 3, "",
    animation=TypewriterAnimation(
        [
            "Game Development",
            "Data Science & Data Analysis",
            "Web Development",
            "Mobile Development",
        ],
        colors=["red", "blue", "green", "yellow"],
        speed=0.04,
        cursor=True,
    )
))

box.add(Label(2, 4, "we have a solution for you."))

box.add(AnimatedLabel(
    2, 7, "Hello World!",
    animation=DecodeAnimation(randomize=True, mode="hex", loop=True, speed=0.06),
))

btn = Button(4, 10, "Quit")
btn.on_click(lambda _: app.quit())

box.add(btn)

app.add(box)
app.focus(btn)
app.run()
