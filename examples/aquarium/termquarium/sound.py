"""Sound: playback for the sounds/ folder (ambience loops + one-shot SFX).

Optional and lazily imported, exactly like the RestrictedPython the Cheat
Console's run() command needs -- `pip install miniaudio` unlocks this, and
every caller here (aquarium.py) checks `available()` first, so a machine
without it (or without a usable audio device at all) just plays the game in
silence instead of crashing.

miniaudio has no built-in channel/mixer API (unlike e.g. pygame.mixer), so
this hand-rolls the smallest one that covers what the asset set actually
needs: one looping ambience track (day/night/forest/storm) plus any number
of overlapping one-shot SFX at once (a click landing while a coin sound is
still playing shouldn't cut either off). Every file is decoded up front to
the exact same format (SIGNED16/44100Hz/stereo) via miniaudio.decode_file's
own output arguments, so mixing is just sample-by-sample addition with
clipping -- no resampling or format-juggling at mix time. A single
PlaybackDevice runs one callback generator that does that mixing; `_active`
is the list of currently-playing sources it reads from, guarded by a lock
since the callback fires on miniaudio's own audio thread, not the main one.
"""

from __future__ import annotations

import array
import threading
from pathlib import Path

try:
    import miniaudio
except ImportError:  # pragma: no cover -- exercised via available() instead
    miniaudio = None

SOUNDS_DIR = Path(__file__).resolve().parent.parent / "sounds"
SAMPLE_RATE = 44100
CHANNELS = 2

# Ambience sits behind SFX, not level with it -- applied at mix time (per-
# _Source volume), not baked into the decoded/cached samples, so it's one
# number to retune without regenerating any audio.
AMBIENCE_VOLUME = 0.45

SFX_FILES = {
    "achievement": "wav/achievement.wav",
    "adventure": "wav/adventure.wav",
    "buy": "wav/buy.wav",
    "click": "wav/click.wav",
    "coin": "wav/coin.wav",
    "dream": "wav/dream.wav",
    "feed": "wav/feed.wav",
    "fish_spawn": "wav/fish_spawn.wav",
    "friend": "wav/friend.wav",
    "hide": "wav/hide.wav",
    "open": "wav/open.wav",
    "return": "wav/return.wav",
    "rival": "wav/rival.wav",
    "save": "wav/save.wav",
    "shark_scare": "wav/shark_scare.wav",
    "sleep": "wav/sleep.wav",
    "wake": "wav/wake.wav",
}
AMBIENCE_FILES = {
    # Replacements for the original ogg/termquarium_*.ogg tracks, which
    # turned out (per direct FFT analysis, not just ear) to be near-static
    # one/two-note drones -- e.g. "day" and "night" spent nearly the entire
    # loop on just two held pitches. These are synthesized instead
    # (evolving 4-chord pad progressions + filtered-noise environmental
    # texture -- water/wind/rain, no melodic instrument at all), generated
    # by a one-off numpy script (not part of the shipped game). Kept in
    # their own sounds/ambience/ folder rather than sounds/wav/ -- these are
    # organized by *role* (ambience vs. one-shot SFX), not by format, unlike
    # the wav/ogg split above. The original ogg files are untouched on disk
    # if they're ever wanted back.
    "day": "ambience/ambience_day.wav",
    "night": "ambience/ambience_night.wav",
    "forest": "ambience/ambience_forest.wav",
    "storm": "ambience/ambience_storm.wav",
}

_lock = threading.Lock()
_active: list["_Source"] = []
_ambience: "_Source | None" = None
_cache: dict[str, array.array] = {}
_device = None  # miniaudio.PlaybackDevice once init() succeeds, else None


class _Source:
    __slots__ = ("samples", "pos", "loop", "volume")

    def __init__(self, samples: array.array, loop: bool, volume: float = 1.0):
        self.samples = samples
        self.pos = 0
        self.loop = loop
        self.volume = volume


def _advance(src: "_Source", nsamples: int):
    """The next `nsamples` interleaved int16 values from `src`, advancing
    its position -- wrapping seamlessly mid-chunk for a looping source, or
    zero-padding the tail once a one-shot runs out. None once a one-shot has
    nothing left at all, telling the mixer to drop it."""
    total = len(src.samples)
    if src.pos >= total and not src.loop:
        return None
    out = array.array("h", bytes(nsamples * 2))
    filled = 0
    while filled < nsamples:
        if src.pos >= total:
            if not src.loop:
                break
            src.pos = 0
        take = min(nsamples - filled, total - src.pos)
        out[filled : filled + take] = src.samples[src.pos : src.pos + take]
        src.pos += take
        filled += take
    return out if filled > 0 else None


def _mixer_generator():
    # miniaudio.PlaybackDevice.start()'s own contract: the generator must
    # already be primed with one next() (yielding an empty result) before
    # it's handed over -- see init() below. The prime's `yield` must be the
    # *only* one that returns empty: `frame_count = yield chunk` inside the
    # loop both hands back whatever chunk was just mixed *and* receives the
    # next requested frame count in the same step, so the very first real
    # send() after priming already returns real mixed data instead of the
    # empty chunk one send too early (an easy off-by-one to get backwards).
    frame_count = yield array.array("h")
    while True:
        nsamples = frame_count * CHANNELS
        mix = [0] * nsamples
        with _lock:
            sources = list(_active)
        still_active = []
        for src in sources:
            data = _advance(src, nsamples)
            if data is None:
                continue
            vol = src.volume
            if vol == 1.0:
                for i in range(len(data)):
                    mix[i] += data[i]
            else:
                for i in range(len(data)):
                    mix[i] += data[i] * vol
            if src.loop or src.pos < len(src.samples):
                still_active.append(src)
        with _lock:
            _active[:] = still_active
        chunk = array.array(
            "h", (int(min(32767, max(-32768, v))) for v in mix)
        )
        frame_count = yield chunk


def available() -> bool:
    """False the moment miniaudio isn't installed -- callers check this
    before bothering to init()/play anything."""
    return miniaudio is not None


def init() -> bool:
    """Start the single mixing PlaybackDevice. Safe to call more than once
    (a no-op past the first success) and safe to call when unavailable (or
    when the machine genuinely has no audio device) -- returns whether
    sound actually ended up usable, but never raises."""
    global _device
    if not available():
        return False
    if _device is not None:
        return True
    try:
        device = miniaudio.PlaybackDevice(
            output_format=miniaudio.SampleFormat.SIGNED16,
            nchannels=CHANNELS,
            sample_rate=SAMPLE_RATE,
        )
        gen = _mixer_generator()
        next(gen)
        device.start(gen)
    except Exception:
        # No audio device, a backend init failure, etc. -- the game plays
        # in silence rather than crashing over a missing sound card.
        return False
    _device = device
    return True


def shutdown() -> None:
    """Stop and close the PlaybackDevice -- aquarium.py calls this once,
    after app.run() returns. miniaudio's device keeps its own background
    thread alive for as long as it's open, which otherwise leaves the
    process hanging on exit even after the game's own event loop and
    terminal cleanup are done. A no-op if init() was never called (or never
    succeeded)."""
    global _device
    if _device is None:
        return
    try:
        _device.stop()
        _device.close()
    except Exception:
        pass
    _device = None
    stop_all()


def _decode(path: Path) -> array.array | None:
    if not path.is_file():
        return None
    try:
        sound = miniaudio.decode_file(
            str(path),
            output_format=miniaudio.SampleFormat.SIGNED16,
            nchannels=CHANNELS,
            sample_rate=SAMPLE_RATE,
        )
    except Exception:
        return None
    return sound.samples


def _cached(key: str, files: dict) -> array.array | None:
    if key in _cache:
        return _cache[key]
    rel = files.get(key)
    if rel is None:
        return None
    samples = _decode(SOUNDS_DIR / rel)
    if samples is not None:
        _cache[key] = samples
    return samples


def play_sfx(name: str) -> None:
    """Fire-and-forget a one-shot from SFX_FILES -- overlaps whatever else
    is already playing rather than cutting it off."""
    if _device is None:
        return
    samples = _cached(name, SFX_FILES)
    if samples is None:
        return
    with _lock:
        _active.append(_Source(samples, loop=False))


def play_ambience(name: str) -> None:
    """Swap the single looping ambience track -- a no-op if `name` is
    already the one playing, so callers can resync unconditionally
    (aquarium.py's _sync_ambience()) without listening for a click every
    time nothing actually changed."""
    global _ambience
    if _device is None:
        return
    samples = _cached(name, AMBIENCE_FILES)
    if samples is None:
        return
    with _lock:
        if _ambience is not None and _ambience.samples is samples:
            return
        if _ambience is not None and _ambience in _active:
            _active.remove(_ambience)
        _ambience = _Source(samples, loop=True, volume=AMBIENCE_VOLUME)
        _active.append(_ambience)


def stop_ambience() -> None:
    global _ambience
    with _lock:
        if _ambience is not None and _ambience in _active:
            _active.remove(_ambience)
        _ambience = None


def stop_all() -> None:
    """Settings' Sound checkbox, turned off -- silence takes effect
    immediately rather than "next time an overlay opens" (Auto-Pause's own
    convention), since muting is meant to be instant."""
    global _ambience
    with _lock:
        _active.clear()
        _ambience = None
