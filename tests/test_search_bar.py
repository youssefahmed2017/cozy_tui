from cozy_tui import App, Style
from cozy_tui.events import Key, MouseClick
from cozy_tui.widgets import SearchBar
from cozy_tui.widgets.selection._search_palette import fuzzy_score


def make_app(**kw):
    return App(full=False, size="400x200", style=Style(fg="white", bg="black"), **kw)


# ── fuzzy_score (pure function) ──────────────────────────────────────────────


def test_fuzzy_score_none_when_not_a_subsequence():
    assert fuzzy_score("cozy_tui", "xyz") is None


def test_fuzzy_score_exact_substring_outranks_loose_subsequence():
    exact = fuzzy_score("command_palette", "command")
    loose = fuzzy_score("command_palette", "cmdp")
    assert exact is not None and loose is not None
    assert exact > loose


def test_fuzzy_score_earlier_substring_scores_higher():
    early = fuzzy_score("abcfoo", "foo")
    late = fuzzy_score("xxxabcfoo", "foo")
    assert early > late


def test_fuzzy_score_case_insensitive():
    assert fuzzy_score("Cozy_TUI", "cozy") == fuzzy_score("cozy_tui", "cozy")


def test_fuzzy_score_empty_query_matches_everything_with_zero_score():
    assert fuzzy_score("anything", "") == 0.0


# ── SearchBar: construction / defaults ──────────────────────────────────────


def test_defaults_to_all_items_unfiltered():
    sb = SearchBar(0, 0, ["a", "b", "c"])
    assert sb.matches == ["a", "b", "c"]
    assert sb.selected == "a"
    assert sb.query == ""


def test_empty_items_has_no_selection():
    sb = SearchBar(0, 0, [])
    assert sb.matches == []
    assert sb.selected is None


# ── substring filtering (default) ────────────────────────────────────────────


def test_substring_filter_is_case_insensitive():
    sb = SearchBar(0, 0, ["Apple", "Banana", "Grape", "Pineapple"])
    for ch in "APP":
        sb.on_key(ch)
    assert sb.matches == ["Apple", "Pineapple"]


def test_backspace_widens_the_filter_again():
    sb = SearchBar(0, 0, ["apple", "banana"])
    for ch in "ap":
        sb.on_key(ch)
    assert sb.matches == ["apple"]
    sb.on_key(Key.BACKSPACE)
    sb.on_key(Key.BACKSPACE)
    assert sb.matches == ["apple", "banana"]


# ── fuzzy_searching=True ─────────────────────────────────────────────────────


def test_fuzzy_mode_matches_non_contiguous_subsequences():
    sb = SearchBar(0, 0, ["command_palette", "confirm_dialog"], fuzzy_searching=True)
    for ch in "cmdp":
        sb.on_key(ch)
    assert sb.matches == ["command_palette"]  # not a subsequence of confirm_dialog


def test_fuzzy_mode_ranks_by_score_not_original_order():
    sb = SearchBar(
        0, 0, ["xxxfoo", "fooxxx"], fuzzy_searching=True
    )  # "fooxxx" listed second but should rank first (earlier substring)
    for ch in "foo":
        sb.on_key(ch)
    assert sb.matches == ["fooxxx", "xxxfoo"]


def test_non_fuzzy_mode_does_not_match_non_contiguous_subsequences():
    sb = SearchBar(0, 0, ["command_palette"], fuzzy_searching=False)
    for ch in "cmdp":
        sb.on_key(ch)
    assert sb.matches == []


# ── navigation ────────────────────────────────────────────────────────────────


def test_navigation_clamps_without_wrapping():
    sb = SearchBar(0, 0, [str(i) for i in range(5)])
    sb.on_key(Key.UP)  # already at 0
    assert sb._index == 0
    for _ in range(10):
        sb.on_key(Key.DOWN)
    assert sb._index == 4
    sb.on_key(Key.HOME)
    assert sb._index == 0
    sb.on_key(Key.END)
    assert sb._index == 4


def test_scrolls_when_matches_exceed_height():
    sb = SearchBar(0, 0, [str(i) for i in range(10)], height=3)
    for _ in range(5):
        sb.on_key(Key.DOWN)
    assert sb._index == 5
    assert sb._scroll_off == 5 - 3 + 1


# ── callbacks ─────────────────────────────────────────────────────────────────


def test_enter_fires_on_select_with_the_highlighted_match():
    picked = []
    sb = SearchBar(0, 0, ["a", "b", "c"])
    sb.on_select(picked.append)
    sb.on_key(Key.DOWN)
    sb.on_key(Key.ENTER)
    assert picked == ["b"]


def test_on_change_fires_on_every_query_edit():
    seen = []
    sb = SearchBar(0, 0, ["apple", "banana"])
    sb.on_change(seen.append)
    sb.on_key("a")
    sb.on_key("p")
    sb.on_key(Key.BACKSPACE)
    assert seen == ["a", "ap", "a"]


def test_esc_clears_the_query_and_fires_on_change():
    seen = []
    sb = SearchBar(0, 0, ["apple", "banana"])
    sb.on_change(seen.append)
    sb.on_key("a")
    sb.on_key(Key.ESC)
    assert sb.query == ""
    assert sb.matches == ["apple", "banana"]
    assert seen == ["a", ""]


def test_esc_with_empty_query_does_not_fire_on_change():
    seen = []
    sb = SearchBar(0, 0, ["apple"])
    sb.on_change(seen.append)
    sb.on_key(Key.ESC)
    assert seen == []


def test_empty_matches_do_not_crash():
    picked = []
    sb = SearchBar(0, 0, ["apple"])
    sb.on_select(picked.append)
    for ch in "zzz":
        sb.on_key(ch)
    assert sb.matches == []
    sb.on_key(Key.UP)
    sb.on_key(Key.DOWN)
    sb.on_key(Key.ENTER)
    assert picked == []


# ── item mutation API ─────────────────────────────────────────────────────────


def test_set_items_replaces_and_reapplies_the_query():
    sb = SearchBar(0, 0, ["apple"])
    for ch in "av":
        sb.on_key(ch)
    sb.set_items(["avocado", "banana"])
    assert sb.matches == ["avocado"]


def test_append_adds_and_reapplies_the_query():
    sb = SearchBar(0, 0, ["apple"])
    for ch in "av":
        sb.on_key(ch)
    sb.append("avocado")
    sb.append("banana")
    assert sb.matches == ["avocado"]


def test_clear_empties_items_and_query():
    sb = SearchBar(0, 0, ["apple", "banana"])
    sb.on_key("a")
    sb.clear()
    assert sb.query == ""
    assert sb.matches == []


# ── mouse ─────────────────────────────────────────────────────────────────────


def test_mouse_click_on_a_match_row_picks_it():
    picked = []
    sb = SearchBar(0, 0, ["a", "b", "c"])
    sb.on_select(picked.append)
    sb.x, sb.y = 0, 0
    # row 0 is the query row; matches start at row 1.
    sb.on_mouse_click(col=sb.abs_x + 2, row=sb.abs_y + 2)
    assert picked == ["b"]


def test_mouse_click_on_the_query_row_does_nothing():
    picked = []
    sb = SearchBar(0, 0, ["a", "b"])
    sb.on_select(picked.append)
    sb.x, sb.y = 0, 0
    sb.on_mouse_click(col=sb.abs_x, row=sb.abs_y)
    assert picked == []


# ── sizing ────────────────────────────────────────────────────────────────────


def test_natural_height_is_query_row_plus_visible_matches():
    sb = SearchBar(0, 0, [str(i) for i in range(20)], height=5)
    assert sb.natural_height(1) == 6  # 1 query row + min(5, 20)


def test_natural_height_with_no_items_is_still_two_rows():
    sb = SearchBar(0, 0, [])
    assert sb.natural_height(1) == 2  # query row + "no matches" row


# ── App integration (draw / focus) ───────────────────────────────────────────


def test_renders_query_and_matches_when_focused():
    app = make_app()
    sb = SearchBar(0, 0, ["apple", "banana"], placeholder="search...")
    app.add(sb)
    app.focus(sb)
    for ch in "app":
        sb.on_key(ch)
    snap = app.snapshot()
    assert "apple" in snap
    assert "banana" not in snap  # filtered out


def test_placeholder_shows_when_empty_and_unfocused():
    app = make_app()
    sb = SearchBar(0, 0, ["apple"], placeholder="type to search")
    app.add(sb)
    snap = app.snapshot()
    assert "type to search" in snap
