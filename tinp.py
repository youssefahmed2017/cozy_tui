import sys

sys.path.insert(0, ".")

from cozy_tui import App, Label, Style, Tree

app = App()

tree = Tree(2, 2, connectors=True)

project = tree.add("Project")
project.expand()

src = project.add("src")
src.expand()

src.add("main.py")
src.add("app.py")

widgets = src.add("widgets")
widgets.add("button.py")
widgets.add("checkbox.py")

docs = project.add("docs")
docs.add("README.md")

status = Label(
    2,
    22,
    "Up/Down navigate   Right expand   Left collapse/parent   Enter toggle   q quit",
    style=Style(fg="bright_black"),
)


def on_select(node):
    kind = "leaf" if node.is_leaf else ("expanded" if node.expanded else "collapsed")
    status.text = f"{node.text!r}  [{kind}]"


tree.on_select(on_select)

app.add(tree)
app.add(status)
app.on_key("q", app.quit)
app.focus(tree)
app.run()
