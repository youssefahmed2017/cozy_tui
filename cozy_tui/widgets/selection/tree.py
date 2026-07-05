from cozy_tui.events import Key
from cozy_tui.style import Style
from cozy_tui.widget import Widget


class TreeNode:
    """A single node in a Tree.  Call add() to create children."""

    def __init__(self, text: str):
        self.text = text
        self.parent: "TreeNode | None" = None
        self.children: list["TreeNode"] = []
        self.expanded: bool = False
        self.metadata = None  # arbitrary user data slot (matches TableRow.metadata)

    def add(self, text: str) -> "TreeNode":
        """Append a child node and return it."""
        child = TreeNode(text)
        child.parent = self
        self.children.append(child)
        return child

    @property
    def is_leaf(self) -> bool:
        return not self.children

    def expand(self) -> None:
        self.expanded = True

    def collapse(self) -> None:
        self.expanded = False

    def toggle(self) -> None:
        if self.children:
            self.expanded = not self.expanded


class Tree(Widget):
    """A navigable tree view widget.

    Pass connectors=True to render branch lines (├──, └──, │).

    Keys: Up/Down navigate visible rows, Right expand, Left collapse (or jump
    to parent when already collapsed), Enter/Space toggle, Home first, End last.
    """

    focusable = True

    def __init__(
        self, x, y, *, height: int | None = None, connectors: bool = False, style=None
    ):
        super().__init__(x, y, style)
        self._roots: list[TreeNode] = []
        self._index: int = 0
        self._scroll_off: int = 0
        self.height = height
        self.connectors = connectors
        self._select_handler = None

    # -- tree-building API ----------------------------------------------------

    def add(self, text: str) -> TreeNode:
        node = TreeNode(text)
        self._roots.append(node)
        return node

    # -- visible list ---------------------------------------------------------

    def _visible(self) -> list[tuple[TreeNode, int, list[bool]]]:
        """DFS walk returning (node, depth, path_last).

        path_last[i] is True when the node at depth i on the root-to-node path
        was the last child of its parent.
        """
        result: list[tuple[TreeNode, int, list[bool]]] = []

        def walk(node: TreeNode, depth: int, path_last: list[bool]) -> None:
            result.append((node, depth, path_last))
            if node.expanded:
                n = len(node.children)
                for i, child in enumerate(node.children):
                    walk(child, depth + 1, path_last + [i == n - 1])

        n_roots = len(self._roots)
        for i, root in enumerate(self._roots):
            walk(root, 0, [i == n_roots - 1])

        return result

    # -- connector rendering --------------------------------------------------

    @staticmethod
    def _connector(depth: int, path_last: list[bool]) -> str:
        """Return the connector prefix string for a node at *depth*.

        Each of the depth columns is 4 chars wide:
          - Pass-through columns (0..depth-2): show vertical bar when the
            depth-(col+1) ancestor was NOT the last child.
          - Connection column (depth-1): show the branch character.
        """
        if depth == 0:
            return ""
        parts = []
        for col in range(depth):
            if col < depth - 1:
                parts.append("    " if path_last[col + 1] else "│   ")
            else:
                parts.append("└── " if path_last[depth] else "├── ")
        return "".join(parts)

    # -- scroll / index helpers -----------------------------------------------

    def _clamp(self, vis_len: int) -> None:
        if vis_len == 0:
            self._index = 0
            self._scroll_off = 0
            return
        self._index = max(0, min(self._index, vis_len - 1))
        h = self.height or vis_len
        if self._index < self._scroll_off:
            self._scroll_off = self._index
        elif self._index >= self._scroll_off + h:
            self._scroll_off = self._index - h + 1

    @staticmethod
    def _index_of(node: TreeNode, vis: list) -> int | None:
        for i, (n, _d, _p) in enumerate(vis):
            if n is node:
                return i
        return None

    @property
    def roots(self):
        return tuple(self._roots)

    # -- callbacks ------------------------------------------------------------

    def on_select(self, func):
        """func(node) fires on Enter or click."""
        self._select_handler = func
        return self

    # -- Widget interface -----------------------------------------------------

    def natural_width(self, scale) -> int:
        vis = self._visible()
        if not vis:
            return 4
        return max(depth * 4 + 2 + len(node.text) for node, depth, _ in vis)

    def natural_height(self, scale) -> int:
        n = len(self._visible())
        return self.height or max(1, n)

    def on_key(self, key) -> None:
        vis = self._visible()
        if not vis:
            return
        n = len(vis)
        self._clamp(n)
        node, depth, path_last = vis[self._index]

        if key == Key.UP:
            if self._index > 0:
                self._index -= 1
                self._clamp(n)
                self._fire_change(vis[self._index][0])

        elif key == Key.DOWN:
            if self._index < n - 1:
                self._index += 1
                self._clamp(n)
                self._fire_change(vis[self._index][0])

        elif key == Key.HOME:
            self._index = 0
            self._clamp(n)
            self._fire_change(vis[0][0])

        elif key == Key.END:
            self._index = n - 1
            self._clamp(n)
            self._fire_change(vis[n - 1][0])

        elif key == Key.RIGHT:
            if not node.is_leaf and not node.expanded:
                node.expand()

        elif key == Key.LEFT:
            if node.expanded:
                node.collapse()
            elif node.parent is not None:
                idx = self._index_of(node.parent, vis)
                if idx is not None:
                    self._index = idx
                    self._clamp(n)
                    self._fire_change(node.parent)

        elif key in (Key.ENTER, " "):
            node.toggle()
            if self._select_handler:
                self._select_handler(node)

    def on_mouse_click(self, col=None, row=None) -> None:
        if row is None:
            return
        vis = self._visible()
        idx = self._scroll_off + (row - self.abs_y)
        if 0 <= idx < len(vis):
            node, _d, _p = vis[idx]
            self._index = idx
            self._clamp(len(vis))
            node.toggle()
            if self._select_handler:
                self._select_handler(node)
            self._fire_change(node)

    def draw(self, canvas) -> None:
        is_focused = canvas.focused is self
        vis = self._visible()
        n = len(vis)
        rows_to_show = self.height or n
        w = self.natural_width(1)

        for row in range(rows_to_show):
            idx = self._scroll_off + row
            vy = self.abs_y + row

            if idx >= n:
                canvas.write(self.abs_x, vy, " " * w, self.style)
                continue

            node, depth, path_last = vis[idx]
            is_sel = is_focused and idx == self._index

            if self.connectors:
                prefix = self._connector(depth, path_last)
            else:
                prefix = " " * (depth * 4)

            if node.children:
                prefix += "v " if node.expanded else "> "
            else:
                prefix += "  "

            line = (prefix + node.text).ljust(w)[:w]

            if is_sel:
                style = Style(fg="black", bg="white", styles=["bold"])
            else:
                style = self.style

            canvas.write(self.abs_x, vy, line, style)
