"""Calendar widget: month-grid generation, cursor/selection split (RadioSet-
style), keyboard/mouse navigation, and theme-driven rendering."""

import calendar as _calendar
from datetime import date

from cozy_tui import App, Style, Theme, get_theme, set_theme
from cozy_tui.events import Key
from cozy_tui.style import selection_style
from cozy_tui.widgets import Calendar


def make_app():
    return App(full=False, size="400x300", style=Style(fg="white", bg="black"))


# ── month grid ────────────────────────────────────────────────────────────────


def test_month_weeks_matches_stdlib_calendar():
    cal = Calendar(0, 0, selected=date(2026, 7, 1))
    expected = _calendar.Calendar(0).monthdayscalendar(2026, 7)
    assert cal._month_weeks() == expected


def test_five_week_and_six_week_months():
    # February 2026 (starts Sunday, 28 days) -> 5 rows; July 2026 -> 5 rows
    # too; pick a month/first_weekday combo known to need 6.
    cal6 = Calendar(0, 0, selected=date(2026, 8, 1))  # Aug 2026 starts Saturday
    assert len(cal6._month_weeks()) == 6
    cal5 = Calendar(0, 0, selected=date(2026, 7, 1))
    assert len(cal5._month_weeks()) == 5


def test_natural_height_matches_week_count():
    cal = Calendar(0, 0, selected=date(2026, 8, 1))
    assert cal.natural_height(1) == 2 + len(cal._month_weeks())


def test_natural_width_is_fixed():
    assert Calendar(0, 0).natural_width(1) == 21


# ── defaults ──────────────────────────────────────────────────────────────────


def test_cursor_defaults_to_today_but_nothing_is_selected():
    cal = Calendar(0, 0)
    assert cal._cursor == date.today()
    assert cal.selected is None


def test_selected_param_sets_both_cursor_and_selection():
    cal = Calendar(0, 0, selected=date(2026, 3, 5))
    assert cal._cursor == date(2026, 3, 5)
    assert cal.selected == date(2026, 3, 5)


# ── keyboard navigation ───────────────────────────────────────────────────────


def test_left_right_move_by_one_day():
    cal = Calendar(0, 0, selected=date(2026, 7, 15))
    cal.on_key(Key.RIGHT)
    assert cal._cursor == date(2026, 7, 16)
    cal.on_key(Key.LEFT)
    cal.on_key(Key.LEFT)
    assert cal._cursor == date(2026, 7, 14)


def test_up_down_move_by_one_week():
    cal = Calendar(0, 0, selected=date(2026, 7, 15))
    cal.on_key(Key.DOWN)
    assert cal._cursor == date(2026, 7, 22)
    cal.on_key(Key.UP)
    cal.on_key(Key.UP)
    assert cal._cursor == date(2026, 7, 8)


def test_day_navigation_crosses_month_boundary():
    cal = Calendar(0, 0, selected=date(2026, 7, 31))
    cal.on_key(Key.RIGHT)
    assert cal._cursor == date(2026, 8, 1)


def test_home_end_land_on_first_and_last_day_of_displayed_month():
    cal = Calendar(0, 0, selected=date(2026, 7, 15))
    cal.on_key(Key.HOME)
    assert cal._cursor == date(2026, 7, 1)
    cal.on_key(Key.END)
    assert cal._cursor == date(2026, 7, 31)


def test_ctrl_left_right_shift_a_month_keeping_day_of_month():
    cal = Calendar(0, 0, selected=date(2026, 6, 15))
    cal.on_key(Key.CTRL_RIGHT)
    assert cal._cursor == date(2026, 7, 15)
    cal.on_key(Key.CTRL_LEFT)
    cal.on_key(Key.CTRL_LEFT)
    assert cal._cursor == date(2026, 5, 15)


def test_ctrl_right_clamps_when_target_month_is_shorter():
    cal = Calendar(0, 0, selected=date(2026, 1, 31))
    cal.on_key(Key.CTRL_RIGHT)
    assert cal._cursor == date(2026, 2, 28)  # 2026 is not a leap year


# ── selection ─────────────────────────────────────────────────────────────────


def test_enter_commits_selection_and_fires_on_select_and_on_click():
    cal = Calendar(0, 0, selected=date(2026, 7, 1))
    cal.on_key(Key.RIGHT)  # cursor -> July 2, not yet selected
    assert cal.selected == date(2026, 7, 1)

    picked = []
    clicked = []
    cal.on_select(picked.append)
    cal.on_click(clicked.append)
    cal.on_key(Key.ENTER)
    assert cal.selected == date(2026, 7, 2)
    assert picked == [date(2026, 7, 2)]
    assert clicked == [cal]


def test_space_also_commits_selection():
    cal = Calendar(0, 0, selected=date(2026, 7, 1))
    cal.on_key(Key.RIGHT)
    cal.on_key(" ")
    assert cal.selected == date(2026, 7, 2)


def test_select_sets_cursor_and_selection_and_fires_on_select_but_not_on_click():
    cal = Calendar(0, 0)
    picked = []
    clicked = []
    cal.on_select(picked.append)
    cal.on_click(clicked.append)
    cal.select(date(2026, 9, 9))
    assert cal.selected == date(2026, 9, 9)
    assert cal._cursor == date(2026, 9, 9)
    assert picked == [date(2026, 9, 9)]
    assert clicked == []  # not an activation gesture


def test_mouse_click_on_a_day_moves_cursor_and_selects():
    app = make_app()
    cal = Calendar(2, 1, selected=date(2026, 7, 1))
    app.add(cal)
    app.focus(cal)
    app.snapshot()

    weeks = cal._month_weeks()
    for week_idx, week in enumerate(weeks):
        if 15 in week:
            day_idx = week.index(15)
            row = cal.abs_y + 2 + week_idx
            col = cal.abs_x + day_idx * 3
            cal.on_mouse_click(col + 1, row)
            break
    assert cal.selected == date(2026, 7, 15)
    assert cal._cursor == date(2026, 7, 15)


def test_mouse_click_on_a_blank_cell_is_a_noop():
    app = make_app()
    cal = Calendar(2, 1, selected=date(2026, 7, 15))
    app.add(cal)
    app.snapshot()
    weeks = cal._month_weeks()
    # first row's leading blanks (0s) for July 2026 (starts Wed w/ Monday-first)
    row = cal.abs_y + 2
    col = cal.abs_x  # first column, first week -- known blank for July 2026
    assert weeks[0][0] == 0
    cal.on_mouse_click(col, row)
    assert cal.selected == date(2026, 7, 15)  # unchanged


def test_clicking_header_arrows_changes_month_not_selection():
    app = make_app()
    cal = Calendar(2, 1, selected=date(2026, 7, 15))
    app.add(cal)
    app.snapshot()  # populates _prev_arrow_col/_next_arrow_col

    cal.on_mouse_click(cal._next_arrow_col, cal.abs_y)
    assert cal._cursor == date(2026, 8, 15)
    assert cal.selected == date(2026, 7, 15)  # unchanged

    cal.on_mouse_click(cal._prev_arrow_col, cal.abs_y)
    cal.on_mouse_click(cal._prev_arrow_col, cal.abs_y)
    assert cal._cursor == date(2026, 6, 15)
    assert cal.selected == date(2026, 7, 15)


# ── rendering / theme ─────────────────────────────────────────────────────────


def _cell_style(app, cal, day):
    y = cal.abs_y + 2
    for week in cal._month_weeks():
        if day in week:
            day_idx = week.index(day)
            return app.buffer[y][cal.abs_x + day_idx * 3].style
        y += 1
    raise AssertionError(f"day {day} not found in the rendered month")


def test_cursor_uses_selection_style_when_focused():
    app = make_app()
    cal = Calendar(2, 1, selected=date(2026, 7, 15))
    app.add(cal)
    app.focus(cal)
    app.snapshot()
    style = _cell_style(app, cal, 15)
    expected = selection_style()
    assert style.fg == expected.fg and style.bg == expected.bg


def test_cursor_is_dimmed_when_not_focused():
    app = make_app()
    cal = Calendar(2, 1, selected=date(2026, 7, 15))
    app.add(cal)
    app.snapshot()  # never focused
    style = _cell_style(app, cal, 15)
    expected = selection_style(dim=True)
    assert style.fg == expected.fg and style.bg == expected.bg


def test_selected_day_uses_accent_when_not_the_cursor():
    app = make_app()
    cal = Calendar(2, 1, selected=date(2026, 7, 10))
    cal._cursor = date(2026, 7, 20)  # cursor elsewhere
    app.add(cal)
    app.snapshot()
    theme = get_theme()
    style = _cell_style(app, cal, 10)
    assert style.fg == theme.accent
    assert "bold" in style.styles


def test_colors_follow_an_active_theme_switch(monkeypatch):
    original = get_theme()
    try:
        set_theme(Theme(mode="monochromatic"))
        app = make_app()
        cal = Calendar(2, 1, selected=date(2026, 7, 10))
        cal._cursor = date(2026, 7, 20)
        app.add(cal)
        app.snapshot()
        theme = get_theme()
        style = _cell_style(app, cal, 10)
        assert style.fg == theme.accent
    finally:
        set_theme(original)


def test_calendar_is_focusable():
    assert Calendar(0, 0).focusable is True


# ── click-the-header drill up/down (Windows-style month/year zoom) ──────────


def test_clicking_header_enters_months_view_with_cursor_on_current_month():
    app = make_app()
    cal = Calendar(2, 1, selected=date(2026, 7, 15))
    app.add(cal)
    app.snapshot()  # populates _header_row/_prev_arrow_col/_next_arrow_col

    cal.on_mouse_click(cal._prev_arrow_col + 1, cal._header_row)
    assert cal._view == "months"
    assert cal._view_year == 2026
    assert cal._grid_cursor == 6  # July -> index 6


def test_clicking_months_header_enters_years_view():
    app = make_app()
    cal = Calendar(2, 1, selected=date(2026, 7, 15))
    app.add(cal)
    app.snapshot()
    cal._drill_up()
    app.snapshot()  # re-populate header coords for the months view

    cal.on_mouse_click(cal._prev_arrow_col + 1, cal._header_row)
    assert cal._view == "years"
    assert cal._years_start <= 2026 <= cal._years_start + 11
    assert cal._grid_cursor == 2026 - cal._years_start


def test_picking_a_month_returns_to_days_without_changing_selection():
    cal = Calendar(0, 0, selected=date(2026, 7, 15))
    cal._enter_months_view(2026)
    cal._grid_cursor = 2  # March (index 2)
    cal._activate_grid_cursor()
    assert cal._view == "days"
    assert cal._cursor == date(2026, 3, 15)
    assert cal.selected == date(2026, 7, 15)  # unchanged -- navigation, not a pick


def test_picking_a_month_clamps_the_day_if_the_target_month_is_shorter():
    cal = Calendar(0, 0, selected=date(2026, 1, 31))
    cal._enter_months_view(2026)
    cal._grid_cursor = 1  # February (index 1), 2026 is not a leap year
    cal._activate_grid_cursor()
    assert cal._cursor == date(2026, 2, 28)


def test_picking_a_year_returns_to_months_view():
    cal = Calendar(0, 0, selected=date(2026, 7, 15))
    cal._enter_years_view()
    target_idx = 2030 - cal._years_start
    cal._grid_cursor = target_idx
    cal._activate_grid_cursor()
    assert cal._view == "months"
    assert cal._view_year == 2030


def test_arrow_click_in_months_view_shifts_by_year():
    app = make_app()
    cal = Calendar(2, 1, selected=date(2026, 7, 15))
    app.add(cal)
    cal._enter_months_view(2026)
    app.snapshot()
    cal.on_mouse_click(cal._next_arrow_col, cal._header_row)
    assert cal._view == "months"
    assert cal._view_year == 2027
    cal.on_mouse_click(cal._prev_arrow_col, cal._header_row)
    cal.on_mouse_click(cal._prev_arrow_col, cal._header_row)
    assert cal._view_year == 2025


def test_arrow_click_in_years_view_shifts_by_twelve():
    app = make_app()
    cal = Calendar(2, 1, selected=date(2026, 7, 15))
    app.add(cal)
    cal._enter_years_view()
    start = cal._years_start
    app.snapshot()
    cal.on_mouse_click(cal._next_arrow_col, cal._header_row)
    assert cal._view == "years"
    assert cal._years_start == start + 12


def test_esc_steps_back_a_level_and_is_a_noop_in_days_view():
    cal = Calendar(0, 0, selected=date(2026, 7, 15))
    cal._drill_up()
    cal._drill_up()
    assert cal._view == "years"
    cal.on_key(Key.ESC)
    assert cal._view == "months"
    cal.on_key(Key.ESC)
    assert cal._view == "days"
    cal.on_key(Key.ESC)  # no-op
    assert cal._view == "days"


def test_grid_cursor_moves_within_the_twelve_cell_grid():
    cal = Calendar(0, 0, selected=date(2026, 7, 1))
    cal._enter_months_view(2026)
    cal._grid_cursor = 0
    cal.on_key(Key.RIGHT)
    assert cal._grid_cursor == 1
    cal.on_key(Key.DOWN)
    assert cal._grid_cursor == 5  # +4 (grid is 4 cols wide)
    cal.on_key(Key.LEFT)
    assert cal._grid_cursor == 4
    cal.on_key(Key.UP)
    assert cal._grid_cursor == 0
    cal.on_key(Key.LEFT)  # wraps
    assert cal._grid_cursor == 11
    cal.on_key(Key.ENTER)
    assert cal._view == "days"  # December picked


def test_natural_size_in_months_and_years_view():
    cal = Calendar(0, 0, selected=date(2026, 7, 1))
    cal._enter_months_view(2026)
    assert cal.natural_width(1) == 20
    assert cal.natural_height(1) == 4
    cal._enter_years_view()
    assert cal.natural_width(1) == 20
    assert cal.natural_height(1) == 4


def test_grid_cursor_style_and_theme_colors_in_months_view():
    app = make_app()
    cal = Calendar(2, 1, selected=date(2026, 3, 10))
    cal._enter_months_view(2026)
    app.add(cal)
    app.focus(cal)
    app.snapshot()
    theme = get_theme()

    row0 = app.buffer[cal.abs_y + 1]
    # cursor is on March (index 2, matching the selected date's month)
    cursor_cell = row0[cal.abs_x + 2 * 5]
    expected = selection_style()
    assert cursor_cell.style.fg == expected.fg and cursor_cell.style.bg == expected.bg


def test_select_forces_view_back_to_days():
    cal = Calendar(0, 0)
    cal._drill_up()
    cal._drill_up()
    assert cal._view == "years"
    cal.select(date(2026, 5, 5))
    assert cal._view == "days"
    assert cal.selected == date(2026, 5, 5)
