import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App
from cozy_tui.widgets import Box, Button, Label, AnimatedLabel, TypewriterAnimation

app = App(full=True)

box = Box(2, 1, "600x300", title="JetBrains Sponser", border="rounded")

box.add(Label(2, 2, "Whether you do"))

box.add(AnimatedLabel(
    2, 3, "",
    animation=TypewriterAnimation(
        ["Game Development", "Data Structures & Analysis", "Web Development"],
        speed=0.07,
        pause=20,
        cursor=True,
    )
))

box.add(Label(2, 4, "We have a solution for you."))
btn = Button(4, 7, "Quit")
btn.on_click(lambda _: app.quit())

box.add(btn)

app.add(box)
app.focus(btn)
app.run()
