from cozy_tui import App, Box, Label, Button, MarkdownInput, Style
from cozy_tui.events import Key

app = App(full=True, size=None, style=Style(fg="white", bg="black"))

box = Box(
    2, 1, "2100x660",
    border="rounded",
    style=Style(fg="cyan", bg="black"),
    title=" MarkdownInput Test ",
)

box.add(Label(2, 1, "Focused → raw edit mode    Unfocused → Rich Markdown preview",
              style=Style(fg="bright_black")))
box.add(Label(2, 2, "Tab to preview / edit  │  Enter for new line  │  ESC to quit",
              style=Style(fg="bright_black")))
box.add(Label(2, 3, "─" * 66, style=Style(fg="cyan")))

editor = MarkdownInput(
    2, 5, 66,
    multiline=True,
    placeholder="# Start typing Markdown here...Try **bold**, *italic*, `code`",
    style=Style(fg="white"),
)

preview_btn = Button(2, 18, "Preview / Edit (Tab)", width=24,
                     style=Style(fg="white", bg="bright_black"))
preview_btn.on_click(lambda b: app.focus(editor))

box.add(editor)
box.add(preview_btn)
app.add(box)
app.focus(editor)
app.on_key(Key.ESC, lambda: "quit")
app.run()
