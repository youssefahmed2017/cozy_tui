import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Box, Button, Label

app = App(full=True)

box = Box(2, 1, "600x300", title="Hello", border="rounded")

box.add(Label(2, 2, "Hello, World!"))

btn = Button(4, 7, "Quit")
btn.on_click(lambda _: app.quit())

box.add(btn)

app.add(box)
app.focus(btn)
app.run()
