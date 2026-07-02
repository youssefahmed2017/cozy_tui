from cozy_tui import App, Style


def make_app():
    return App(full=False, size="200x60", style=Style(fg="white", bg="black"))


def test_worker_result_delivered_on_drain():
    app = make_app()
    got = []
    thread = app.run_worker(lambda: 21 + 21, on_result=got.append)
    thread.join(timeout=2)
    assert app._drain_workers() is True
    assert got == [42]


def test_worker_error_routed_to_on_error():
    app = make_app()
    errors = []

    def boom():
        raise ValueError("nope")

    thread = app.run_worker(boom, on_error=errors.append)
    thread.join(timeout=2)
    app._drain_workers()
    assert len(errors) == 1
    assert isinstance(errors[0], ValueError)


def test_drain_with_no_workers_returns_false():
    app = make_app()
    assert app._drain_workers() is False
