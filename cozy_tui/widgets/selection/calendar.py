import calendar as _calendar
from datetime import date, timedelta

from cozy_tui.events import Key
from cozy_tui.style import Style, selection_style
from cozy_tui.widget import Widget

_DAY_WIDTH = 21  # 7 columns x 3 chars ("NN ") each
_GRID_WIDTH = 20  # 4 columns x 5 chars each, for the months/years grids
_GRID_COLS = 4
_GRID_ROWS = 3  # 4x3 = 12 cells: months of a year, or years in a block


class Calendar(Widget):
    """A focusable month-view date picker, backed by the standard library's
    `calendar` module (no new dependency).

    A moving keyboard **cursor** (Left/Right by day, Up/Down by week,
    Ctrl+Left/Ctrl+Right by month) is separate from the committed
    **selection** (Enter/Space, or a click on a day) -- the same
    cursor-vs-selection split :class:`~cozy_tui.widgets.RadioSet` uses.

    Clicking the header (not its ``‹``/``›`` arrows) zooms out one level,
    Windows `MonthCalendar`-style: the day grid zooms out to a 12-month
    grid for the year, which zooms out to a 12-year grid -- clicking a
    month/year zooms back in (to days / to that year's months), landing on
    the same day-of-month/month clamped if the target is shorter, without
    changing the selection (picking a month or year is navigation, not a
    date pick). `Esc` steps back a level from either zoomed-out view; the
    arrows shift by year (months view) or by 12 years (years view) instead
    of by month. `on_select(func)` fires with a `datetime.date` only on an
    actual day pick, never on mere cursor movement or zoom navigation.

    Example::

        cal = Calendar(2, 2)
        cal.on_select(lambda d: print(f"picked {d}"))
        app.add(cal)
    """

    focusable = True

    def __init__(
        self, x, y, *, selected: date | None = None, first_weekday: int = 0, style=None
    ):
        super().__init__(x, y, style, name="Calendar")
        self._cursor: date = selected or date.today()
        self._selected: date | None = selected
        self.first_weekday = first_weekday
        self._select_handler = None
        self._weeks_cache_key = None
        self._weeks_cache: list[list[int]] | None = None
        self._prev_arrow_col: int | None = None
        self._next_arrow_col: int | None = None
        self._header_row: int | None = None

        # Zoom level state: "days" (default) / "months" / "years".
        self._view: str = "days"
        self._view_year: int = self._cursor.year
        self._years_start: int = self._cursor.year - 5
        self._grid_cursor: int = 0  # 0-11 keyboard cursor in "months"/"years"

    # ── selection API (mirrors RadioSet/Table) ───────────────────────────────

    @property
    def selected(self) -> date | None:
        return self._selected

    def select(self, d: date) -> None:
        """Programmatically commit a selection and move the cursor/view
        there. Fires `on_select` (like `RadioSet.select_index`) but not the
        `on_click` activation signal, which is reserved for an actual
        Enter/Space/click gesture."""
        self._cursor = d
        self._selected = d
        self._view = "days"
        if self._select_handler:
            self._select_handler(self._selected)

    def on_select(self, func):
        """Register a callback invoked with the picked `date` when Enter,
        Space, or a day is clicked. Never fires on mere cursor movement."""
        self._select_handler = func
        return self

    def _select_current(self) -> None:
        self._selected = self._cursor
        self._fire_click()  # on_click(widget): fires on Enter/Space or click
        if self._select_handler:
            self._select_handler(self._selected)

    # ── month grid (day view) ────────────────────────────────────────────────

    def _month_weeks(self) -> list[list[int]]:
        key = (self._cursor.year, self._cursor.month, self.first_weekday)
        if key != self._weeks_cache_key:
            self._weeks_cache_key = key
            self._weeks_cache = _calendar.Calendar(
                self.first_weekday
            ).monthdayscalendar(self._cursor.year, self._cursor.month)
        return self._weeks_cache

    def _shift_month(self, delta: int) -> None:
        year, month, day = (
            self._cursor.year,
            self._cursor.month + delta,
            self._cursor.day,
        )
        while month < 1:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1
        last_day = _calendar.monthrange(year, month)[1]
        self._cursor = date(year, month, min(day, last_day))

    def _day_at(self, col: int, row: int) -> int | None:
        local_row = row - self.abs_y - 2
        weeks = self._month_weeks()
        if not (0 <= local_row < len(weeks)):
            return None
        day_idx = (col - self.abs_x) // 3
        if not (0 <= day_idx < 7):
            return None
        return weeks[local_row][day_idx] or None

    # ── zoom navigation (months/years views) ─────────────────────────────────

    def _enter_months_view(self, year: int) -> None:
        self._view_year = year
        self._grid_cursor = self._cursor.month - 1
        self._view = "months"

    def _enter_years_view(self) -> None:
        self._years_start = self._view_year - 5
        self._grid_cursor = self._view_year - self._years_start
        self._view = "years"

    def _pick_month(self, month: int) -> None:
        last_day = _calendar.monthrange(self._view_year, month)[1]
        self._cursor = date(self._view_year, month, min(self._cursor.day, last_day))
        self._view = "days"

    def _activate_grid_cursor(self) -> None:
        if self._view == "months":
            self._pick_month(self._grid_cursor + 1)
        elif self._view == "years":
            self._enter_months_view(self._years_start + self._grid_cursor)

    def _drill_up(self) -> None:
        if self._view == "days":
            self._enter_months_view(self._cursor.year)
        elif self._view == "months":
            self._enter_years_view()
        # "years": no further zoom level -- a header click there is a no-op.

    def _go_back(self) -> None:
        if self._view == "years":
            self._view = "months"
        elif self._view == "months":
            self._view = "days"

    def _shift_current_view(self, delta: int) -> None:
        if self._view == "days":
            self._shift_month(delta)
        elif self._view == "months":
            self._view_year += delta
        elif self._view == "years":
            self._years_start += delta * 12

    def _grid_index_at(self, col: int, row: int) -> int | None:
        local_row = row - self.abs_y - 1
        if not (0 <= local_row < _GRID_ROWS):
            return None
        cell_w = _GRID_WIDTH // _GRID_COLS
        local_col = (col - self.abs_x) // cell_w
        if not (0 <= local_col < _GRID_COLS):
            return None
        idx = local_row * _GRID_COLS + local_col
        return idx if idx < 12 else None

    # ── Widget interface ──────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        return _DAY_WIDTH if self._view == "days" else _GRID_WIDTH

    def natural_height(self, scale) -> int:
        if self._view == "days":
            return 2 + len(self._month_weeks())
        return 1 + _GRID_ROWS

    def on_key(self, key) -> None:
        if self._view == "days":
            self._on_key_days(key)
        else:
            self._on_key_grid(key)

    def _on_key_days(self, key) -> None:
        if key == Key.LEFT:
            self._cursor -= timedelta(days=1)
        elif key == Key.RIGHT:
            self._cursor += timedelta(days=1)
        elif key == Key.UP:
            self._cursor -= timedelta(days=7)
        elif key == Key.DOWN:
            self._cursor += timedelta(days=7)
        elif key == Key.CTRL_LEFT:
            self._shift_month(-1)
        elif key == Key.CTRL_RIGHT:
            self._shift_month(1)
        elif key == Key.HOME:
            self._cursor = self._cursor.replace(day=1)
        elif key == Key.END:
            last_day = _calendar.monthrange(self._cursor.year, self._cursor.month)[1]
            self._cursor = self._cursor.replace(day=last_day)
        elif key in (Key.ENTER, " "):
            self._select_current()

    def _on_key_grid(self, key) -> None:
        if key == Key.LEFT:
            self._grid_cursor = (self._grid_cursor - 1) % 12
        elif key == Key.RIGHT:
            self._grid_cursor = (self._grid_cursor + 1) % 12
        elif key == Key.UP:
            self._grid_cursor = (self._grid_cursor - _GRID_COLS) % 12
        elif key == Key.DOWN:
            self._grid_cursor = (self._grid_cursor + _GRID_COLS) % 12
        elif key in (Key.ENTER, " "):
            self._activate_grid_cursor()
        elif key == Key.ESC:
            self._go_back()

    def on_mouse_click(self, col=None, row=None) -> None:
        if col is None or row is None:
            return
        if row == self._header_row:
            if col == self._prev_arrow_col:
                self._shift_current_view(-1)
            elif col == self._next_arrow_col:
                self._shift_current_view(1)
            else:
                self._drill_up()
            return
        if self._view == "days":
            day = self._day_at(col, row)
            if day is not None:
                self._cursor = date(self._cursor.year, self._cursor.month, day)
                self._select_current()
        else:
            idx = self._grid_index_at(col, row)
            if idx is not None:
                self._grid_cursor = idx
                self._activate_grid_cursor()

    def _draw_header(self, canvas, text: str, width: int) -> None:
        from cozy_tui.theme import get_theme  # local: theme.py builds on Style

        header_style = Style(fg=get_theme().accent, styles=["bold"])
        inner_w = width - 2
        centered = text.center(inner_w)[:inner_w]
        canvas.write(self.abs_x, self.abs_y, "‹" + centered + "›", header_style)
        self._prev_arrow_col = self.abs_x
        self._next_arrow_col = self.abs_x + width - 1
        self._header_row = self.abs_y

    def draw(self, canvas) -> None:
        if self._view == "days":
            self._draw_days(canvas)
        else:
            self._draw_grid(canvas)

    def _draw_days(self, canvas) -> None:
        from cozy_tui.theme import get_theme  # local: theme.py builds on Style

        is_focused = canvas.focused is self
        theme = get_theme()
        header_text = f"{_calendar.month_name[self._cursor.month]} {self._cursor.year}"
        self._draw_header(canvas, header_text, _DAY_WIDTH)
        x, y = self.abs_x, self.abs_y + 1

        weekday_style = Style(fg=theme.muted)
        abbrs = [_calendar.day_abbr[(self.first_weekday + i) % 7][:2] for i in range(7)]
        canvas.write(x, y, "".join(f"{a:>2} " for a in abbrs), weekday_style)
        y += 1

        today = date.today()
        for week in self._month_weeks():
            cx = x
            for day in week:
                if day == 0:
                    canvas.write(cx, y, "   ", self.style)
                    cx += 3
                    continue
                d = date(self._cursor.year, self._cursor.month, day)
                if d == self._cursor:
                    style = (
                        selection_style() if is_focused else selection_style(dim=True)
                    )
                elif d == self._selected:
                    style = Style(fg=theme.accent, styles=["bold"])
                elif d == today:
                    style = Style(fg=theme.accent, styles=["underline"])
                else:
                    style = self.style
                canvas.write(cx, y, f"{day:>2} ", style)
                cx += 3
            y += 1

    def _draw_grid(self, canvas) -> None:
        from cozy_tui.theme import get_theme  # local: theme.py builds on Style

        is_focused = canvas.focused is self
        theme = get_theme()
        today = date.today()

        if self._view == "months":
            header_text = str(self._view_year)
            labels = [_calendar.month_abbr[m] for m in range(1, 13)]
            cell_years = [self._view_year] * 12
            cell_months: list[int | None] = list(range(1, 13))
        else:
            years = list(range(self._years_start, self._years_start + 12))
            header_text = f"{self._years_start}-{self._years_start + 11}"
            labels = [str(yr) for yr in years]
            cell_years = years
            cell_months = [None] * 12

        self._draw_header(canvas, header_text, _GRID_WIDTH)
        x, y = self.abs_x, self.abs_y + 1
        cell_w = _GRID_WIDTH // _GRID_COLS

        def matches(other: date | None, idx: int) -> bool:
            if other is None:
                return False
            if cell_months[idx] is None:
                return other.year == cell_years[idx]
            return other.year == cell_years[idx] and other.month == cell_months[idx]

        for row in range(_GRID_ROWS):
            cx = x
            for col in range(_GRID_COLS):
                idx = row * _GRID_COLS + col
                if idx == self._grid_cursor:
                    style = (
                        selection_style() if is_focused else selection_style(dim=True)
                    )
                elif matches(self._selected, idx):
                    style = Style(fg=theme.accent, styles=["bold"])
                elif matches(today, idx):
                    style = Style(fg=theme.accent, styles=["underline"])
                else:
                    style = self.style
                canvas.write(cx, y, f"{labels[idx]:^{cell_w}}", style)
                cx += cell_w
            y += 1
