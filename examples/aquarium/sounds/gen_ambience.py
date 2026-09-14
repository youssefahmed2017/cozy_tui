"""Generator for TermQuarium's ambience/ loops -- replaced the original
ogg/termquarium_*.ogg tracks, which turned out (per direct FFT analysis,
not just ear) to be near-static one/two-note drones: "day" and "night"
spent nearly their entire 120s loop on just two held pitches. These are
synthesized instead: evolving 4-chord pad progressions (detuned sine
stacks, slowly crossfaded chord to chord) layered with filtered-noise
environmental texture (water/wind/rain/thunder, shaped by FFT-masking
white noise into a soft-edged frequency band) -- no melodic instrument
timbre at all, which is what actually read as "nursery rhyme" before.

Needs numpy (`pip install numpy`) -- a generation-time tool only, never
imported by sound.py or anything else the shipped game runs. Regenerate
with `python sounds/gen_ambience.py sounds/ambience`.
"""

import sys
import wave

import numpy as np

SR = 44100
DUR = 45.0  # shorter than the old 120s loops -- still loops cleanly, faster to iterate on


def midi_to_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pad_layer(chords, seconds, sr=SR, detune_cents=6, n_partials=3, seed=0):
    """A warm evolving pad: each chord is a handful of detuned sine stacks
    per note, crossfaded into the next chord. `chords` is a list of
    (midi_notes, weight) -- weight lets some chords linger longer than
    others so the progression doesn't feel metronomic."""
    rng = np.random.default_rng(seed)
    total_weight = sum(w for _, w in chords)
    n = int(seconds * sr)
    out = np.zeros(n)
    t = np.arange(n) / sr
    boundaries = [0]
    acc = 0.0
    for _, w in chords:
        acc += w / total_weight
        boundaries.append(int(acc * n))
    fade = int(0.15 * sr * min(seconds / len(chords), 8))  # generous crossfade
    for i, (notes, _) in enumerate(chords):
        lo, hi = boundaries[i], boundaries[i + 1]
        seg_n = hi - lo
        if seg_n <= 0:
            continue
        seg_t = t[lo:hi]
        seg = np.zeros(seg_n)
        for note in notes:
            base = midi_to_hz(note)
            for p in range(n_partials):
                detune = 1 + (rng.uniform(-1, 1) * detune_cents / 1200) * (p + 1)
                phase = rng.uniform(0, 2 * np.pi)
                amp = 1.0 / (p + 1) ** 1.3
                seg += amp * np.sin(2 * np.pi * base * detune * seg_t + phase)
        seg /= max(len(notes), 1)
        # fade this segment's own edges so consecutive chords crossfade
        env = np.ones(seg_n)
        f = min(fade, seg_n // 2)
        if f > 0:
            ramp = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, f))
            env[:f] *= ramp
            env[-f:] *= ramp[::-1]
        out[lo:hi] += seg * env
    return out


def filtered_noise(seconds, low_hz, high_hz, sr=SR, seed=1):
    """Bandpass-ish texture via FFT masking of white noise -- water bubbling,
    wind, or rain/thunder rumble depending on the band chosen."""
    rng = np.random.default_rng(seed)
    n = int(seconds * sr)
    noise = rng.normal(0, 1, n)
    spec = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(n, 1 / sr)
    mask = (freqs >= low_hz) & (freqs <= high_hz)
    # soft-edged band, not a brick wall -- avoids a ringing/phasey texture
    window = np.zeros_like(freqs)
    idx = np.where(mask)[0]
    if len(idx):
        w = np.hanning(len(idx) + 2)[1:-1]
        window[idx] = w
    spec *= window
    out = np.fft.irfft(spec, n)
    return out / (np.abs(out).max() + 1e-9)


def slow_lfo(seconds, hz, sr=SR, phase=0.0, depth=0.25, center=0.75):
    t = np.arange(int(seconds * sr)) / sr
    return center + depth * np.sin(2 * np.pi * hz * t + phase)


def normalize(x, peak=0.55):
    m = np.abs(x).max()
    return x * (peak / m) if m > 0 else x


def seamless_loop(x, sr=SR, xfade=3.5):
    """Standard overlap-add loop crossfade: fold the last `n` samples into
    the first `n` (blended tail-to-head), shortening the buffer by `n`.
    The wrap boundary (out[-1] -> out[0]) is then the *original* signal's
    own natural continuity (x[-n-1] -> x[-n]), not an artificial splice."""
    n = min(int(xfade * sr), len(x) // 4)
    if n <= 0:
        return x
    ramp = np.linspace(0, 1, n)
    head, tail = x[:n], x[-n:]
    blended = tail * (1 - ramp) + head * ramp
    return np.concatenate([blended, x[n : len(x) - n]])


def to_stereo(mono, width_ms=9, sr=SR):
    """A cheap Haas-effect widen: a short delay on one channel reads as
    stereo space without any real spatial synthesis. np.roll (wrap), not a
    zero-padded shift -- called *after* seamless_loop(), so mono is already
    loop-safe; zero-padding the start would silence the right channel's
    loop point and reintroduce the exact discontinuity seamless_loop just
    fixed, just on one channel instead of both."""
    d = int(width_ms / 1000 * sr)
    return np.stack([mono, np.roll(mono, d)], axis=1)


def write_wav(path, stereo, sr=SR):
    data = np.clip(stereo, -1.0, 1.0)
    pcm = (data * 32767).astype(np.int16)
    with wave.open(path, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(pcm.tobytes())


# ---- Mood presets -----------------------------------------------------


def make_day():
    # C lydian-leaning pad, gentle major-9th color -- bright but soft, no
    # single held note dominating (the old track's actual problem).
    chords = [
        ([60, 64, 67, 71], 1.3),  # Cmaj9 (no 3rd doubling)
        ([62, 65, 69, 72], 1.0),  # Dm7 passing chord
        ([57, 60, 64, 67], 1.2),  # Am7
        ([60, 64, 67, 74], 1.1),  # Cmaj(add9), higher voicing
    ]
    pad = pad_layer(chords, DUR, seed=10)
    water = filtered_noise(DUR, 400, 3500, seed=11) * slow_lfo(
        DUR, 0.07, phase=0.3, depth=0.5, center=0.5
    )
    mix = normalize(pad, 0.5) + normalize(water, 0.12)
    return to_stereo(seamless_loop(normalize(mix, 0.5)))


def make_night():
    # Lower register, A minor / dorian, slower movement, sparser -- distinct
    # from Day mostly by register + harmonic color, not just "quieter".
    chords = [
        ([45, 48, 52, 57], 1.4),  # Am9 low
        ([43, 47, 50, 55], 1.2),  # F-ish (Dmaj7/A-ish color)
        ([48, 52, 55, 60], 1.3),  # Am (mid)
        ([45, 50, 52, 57], 1.1),
    ]
    pad = pad_layer(chords, DUR, detune_cents=8, seed=20)
    water = filtered_noise(DUR, 200, 1800, seed=21) * slow_lfo(
        DUR, 0.05, phase=1.1, depth=0.4, center=0.35
    )
    crickets = (
        filtered_noise(DUR, 3000, 6000, seed=22)
        * slow_lfo(DUR, 0.6, depth=0.5, center=0.5)
        * 0.06
    )
    mix = normalize(pad, 0.45) + normalize(water, 0.10) + crickets
    return to_stereo(seamless_loop(normalize(mix, 0.42)))


def make_forest():
    # Airier, more open-fifth voicings (less "chordal", more modal drone-ish
    # but still moving) + wind/leaves texture instead of water.
    chords = [
        ([50, 57, 62], 1.3),  # D + open 5th/9th
        ([48, 55, 60], 1.1),  # C-ish open
        ([50, 55, 62, 67], 1.2),
        ([53, 57, 60], 1.0),
    ]
    pad = pad_layer(chords, DUR, detune_cents=10, n_partials=2, seed=30)
    wind = filtered_noise(DUR, 150, 2200, seed=31) * slow_lfo(
        DUR, 0.09, phase=2.0, depth=0.55, center=0.45
    )
    leaves = (
        filtered_noise(DUR, 2500, 8000, seed=32)
        * slow_lfo(DUR, 0.22, depth=0.5, center=0.35)
        * 0.5
    )
    mix = normalize(pad, 0.4) + normalize(wind, 0.22) + normalize(leaves, 0.10)
    return to_stereo(seamless_loop(normalize(mix, 0.48)))


def make_storm():
    # Tense suspended/diminished movement, low rumble + higher rain hiss,
    # bigger amplitude swells -- the one track allowed real dynamic motion.
    chords = [
        ([43, 49, 54], 1.0),  # sus/dim-ish, unresolved
        ([41, 47, 53, 56], 1.2),
        ([44, 50, 53], 0.9),
        ([41, 44, 50, 56], 1.1),
    ]
    pad = pad_layer(chords, DUR, detune_cents=14, n_partials=3, seed=40)
    rumble = filtered_noise(DUR, 40, 220, seed=41) * slow_lfo(
        DUR, 0.12, depth=0.6, center=0.55
    )
    rain = filtered_noise(DUR, 1500, 9000, seed=42) * slow_lfo(
        DUR, 0.17, phase=0.7, depth=0.35, center=0.55
    )
    swell = slow_lfo(DUR, 0.045, depth=0.35, center=0.85)
    mix = (
        normalize(pad, 0.42) + normalize(rumble, 0.30) + normalize(rain, 0.16)
    ) * swell
    return to_stereo(seamless_loop(normalize(mix, 0.55)))


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    presets = [
        ("day", make_day),
        ("night", make_night),
        ("forest", make_forest),
        ("storm", make_storm),
    ]
    for name, fn in presets:
        write_wav(f"{out_dir}/ambience_{name}.wav", fn())
        print(f"wrote {out_dir}/ambience_{name}.wav")
