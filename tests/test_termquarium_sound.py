"""Sound (termquarium/sound.py): pure logic for the hand-rolled mixer
(_advance/_mixer_generator) plus the play_*/available()/init() state
machine, all exercised without a real audio device -- _device is a fake
non-None sentinel wherever a test needs play_sfx()/play_ambience() to
actually append to _active, never a real miniaudio.PlaybackDevice."""

import array

import pytest

from examples.aquarium.termquarium import sound


@pytest.fixture(autouse=True)
def _reset_sound_state():
    """Every test starts from a clean slate and leaves one behind -- this
    module's state (_active/_ambience/_cache/_device) is process-global,
    same reason _headless_app() in test_aquarium.py patches sound.init()
    for every other test in the suite."""
    sound._active.clear()
    sound._ambience = None
    sound._cache.clear()
    sound._device = None
    yield
    sound._active.clear()
    sound._ambience = None
    sound._cache.clear()
    sound._device = None


def _samples(*values: int) -> array.array:
    """A tiny fake mono-interleaved-as-stereo sample buffer for math tests
    -- real files decode to much longer arrays, but the mixing arithmetic
    doesn't care about length."""
    return array.array("h", values)


def test_advance_returns_requested_length_and_advances_position():
    src = sound._Source(_samples(1, 2, 3, 4, 5, 6), loop=False)
    out = sound._advance(src, 4)
    assert list(out) == [1, 2, 3, 4]
    assert src.pos == 4


def test_advance_zero_pads_the_tail_of_a_finishing_one_shot():
    src = sound._Source(_samples(1, 2, 3), loop=False)
    out = sound._advance(src, 5)
    assert list(out) == [1, 2, 3, 0, 0]
    assert src.pos == 3


def test_advance_returns_none_once_a_one_shot_is_fully_exhausted():
    src = sound._Source(_samples(1, 2), loop=False)
    sound._advance(src, 5)  # consumes it, tail zero-padded
    assert sound._advance(src, 5) is None


def test_advance_wraps_seamlessly_mid_chunk_for_a_looping_source():
    src = sound._Source(_samples(10, 20, 30), loop=True)
    out = sound._advance(src, 7)  # 3 + 3 + 1 -- wraps twice within one call
    assert list(out) == [10, 20, 30, 10, 20, 30, 10]
    assert src.pos == 1  # one frame into the third lap


def test_mixer_generator_sums_two_overlapping_sources():
    gen = sound._mixer_generator()
    next(gen)  # prime, per miniaudio.PlaybackDevice.start()'s own contract
    sound._active.append(sound._Source(_samples(100, 200, 300, 400), loop=False))
    sound._active.append(sound._Source(_samples(1, 2, 3, 4), loop=False))

    chunk = gen.send(2)  # 2 frames * CHANNELS(2) = 4 samples

    assert list(chunk) == [101, 202, 303, 404]


def test_mixer_generator_drops_a_finished_one_shot_but_keeps_looping_ambience():
    gen = sound._mixer_generator()
    next(gen)
    one_shot = sound._Source(_samples(5, 5, 5, 5), loop=False)  # exactly 1 frame*2ch...
    ambience = sound._Source(_samples(1, 1), loop=True)
    sound._active.extend([one_shot, ambience])

    gen.send(2)  # consumes the one-shot entirely this tick

    assert one_shot not in sound._active
    assert ambience in sound._active


def test_mixer_generator_clips_to_int16_range():
    gen = sound._mixer_generator()
    next(gen)
    sound._active.append(sound._Source(_samples(30000, -30000), loop=False))
    sound._active.append(sound._Source(_samples(30000, -30000), loop=False))

    chunk = gen.send(1)

    assert list(chunk) == [32767, -32768]


def test_available_reflects_whether_miniaudio_is_importable(monkeypatch):
    monkeypatch.setattr(sound, "miniaudio", None)
    assert sound.available() is False

    monkeypatch.setattr(sound, "miniaudio", object())
    assert sound.available() is True


def test_init_is_a_safe_noop_when_miniaudio_is_unavailable(monkeypatch):
    monkeypatch.setattr(sound, "miniaudio", None)
    assert sound.init() is False
    assert sound._device is None


def test_play_sfx_is_a_noop_before_init(monkeypatch):
    # _device starts None (see the fixture) -- nothing should crash or
    # queue anything without a working device.
    sound.play_sfx("click")
    assert sound._active == []


def test_play_sfx_appends_a_nonlooping_source_using_a_fake_decode(monkeypatch):
    sound._device = object()  # any non-None sentinel -- never touched directly
    monkeypatch.setattr(sound, "_decode", lambda path: _samples(1, 2, 3, 4))

    sound.play_sfx("click")

    assert len(sound._active) == 1
    assert sound._active[0].loop is False
    assert "click" in sound._cache  # decoded once, cached by name


def test_play_sfx_reuses_the_cache_instead_of_redecoding(monkeypatch):
    sound._device = object()
    calls = []

    def _fake_decode(path):
        calls.append(path)
        return _samples(1, 2)

    monkeypatch.setattr(sound, "_decode", _fake_decode)

    sound.play_sfx("click")
    sound.play_sfx("click")

    assert len(calls) == 1
    assert len(sound._active) == 2  # both plays still queued, just one decode


def test_play_sfx_ignores_an_unknown_name(monkeypatch):
    sound._device = object()
    monkeypatch.setattr(sound, "_decode", lambda path: _samples(1, 2))
    sound.play_sfx("not_a_real_sound")
    assert sound._active == []


def test_play_ambience_replaces_the_previous_track(monkeypatch):
    sound._device = object()
    monkeypatch.setattr(
        sound,
        "_decode",
        lambda path: _samples(1, 1) if "day" in str(path) else _samples(2, 2),
    )

    sound.play_ambience("day")
    first = sound._ambience
    sound.play_ambience("night")

    assert first not in sound._active
    assert sound._ambience in sound._active
    assert sound._ambience.loop is True


def test_play_ambience_is_a_noop_when_the_same_track_is_already_playing(monkeypatch):
    sound._device = object()
    monkeypatch.setattr(sound, "_decode", lambda path: _samples(1, 1))

    sound.play_ambience("day")
    playing = sound._ambience
    sound.play_ambience("day")

    assert sound._ambience is playing  # never swapped for an identical track


def test_stop_ambience_removes_it_but_leaves_other_sfx_playing(monkeypatch):
    sound._device = object()
    monkeypatch.setattr(sound, "_decode", lambda path: _samples(1, 1))
    sound.play_ambience("day")
    sound.play_sfx("click")

    sound.stop_ambience()

    assert sound._ambience is None
    assert len(sound._active) == 1  # the click SFX source is untouched


def test_stop_all_clears_everything(monkeypatch):
    sound._device = object()
    monkeypatch.setattr(sound, "_decode", lambda path: _samples(1, 1))
    sound.play_ambience("day")
    sound.play_sfx("click")

    sound.stop_all()

    assert sound._ambience is None
    assert sound._active == []


def test_every_sfx_and_ambience_file_actually_exists_on_disk():
    for rel in sound.SFX_FILES.values():
        assert (sound.SOUNDS_DIR / rel).is_file(), rel
    for rel in sound.AMBIENCE_FILES.values():
        assert (sound.SOUNDS_DIR / rel).is_file(), rel


def test_play_ambience_applies_ambience_volume_but_sfx_stays_at_full_volume(
    monkeypatch,
):
    sound._device = object()
    monkeypatch.setattr(sound, "_decode", lambda path: _samples(1, 1))

    sound.play_ambience("day")
    sound.play_sfx("click")

    assert sound._ambience.volume == sound.AMBIENCE_VOLUME
    sfx_source = next(s for s in sound._active if s is not sound._ambience)
    assert sfx_source.volume == 1.0


def test_mixer_generator_scales_a_quieter_sources_contribution():
    gen = sound._mixer_generator()
    next(gen)
    quiet = sound._Source(_samples(1000, 1000), loop=False, volume=0.5)
    sound._active.append(quiet)

    chunk = gen.send(1)

    assert list(chunk) == [500, 500]
