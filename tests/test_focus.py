from cozy_tui import App, Box, Button, Input, Label, Style


def make_app():
    return App(full=False, size="800x400", style=Style(fg="white", bg="black"))


def test_tab_dives_into_first_child_and_skips_container():
    app = make_app()
    box = Box(2, 1, "400x150", title="Form")
    inp = Input(2, 2, 20)
    btn = Button(2, 5, "OK")
    box.add(Label(2, 4, "hi"))  # non-focusable
    box.add(inp)
    box.add(btn)
    app.add(box)

    stops = app._collect_focusables()
    assert stops == [inp, btn]  # the box itself is not a stop


def test_decorative_box_is_not_focusable_by_default():
    app = make_app()
    box = Box(2, 1, "300x60", title="Info")
    box.add(Label(1, 1, "read only"))
    app.add(box)
    assert app._collect_focusables() == []


def test_opt_in_focusable_box_becomes_a_stop():
    app = make_app()
    box = Box(2, 1, "300x60", title="Panel", focusable=True)
    box.add(Label(1, 1, "panel"))
    app.add(box)
    assert app._collect_focusables() == [box]


def test_default_box_focusable_flag_is_false():
    assert Box(0, 0, "10x10").focusable is False


def test_first_focusable_dives_through_container():
    app = make_app()
    box = Box(2, 1, "400x150")
    inp = Input(2, 2, 20)
    box.add(inp)
    app.add(box)
    assert app._first_focusable(box) is inp
