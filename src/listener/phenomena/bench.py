# SPDX-License-Identifier: Apache-2.0
"""`listener phenomena`: every measure against published facts about the loudness of short and changing sounds.

No listener data for sound effects exist yet. What does exist is a body of results on tones and noises that any
model of event loudness has to reproduce first. Each phenomenon here is a pair of sounds A and B and what listeners
did: the level difference at which B sounds as loud as A (or only its sign, where that is all the literature gives).
Every measure answers the same question: by how many dB would you raise B to make it as loud as A?

Use: (1) a regression suite for any new model, including the event-level model this project will fit; (2) a statement
of what the standard measures already get wrong before any sound effect is involved; (3) for the contrasts nobody has
measured (dry against wet, boom against click), each measure's prediction on record before the listening test.

Stimuli and numbers follow the papers where the papers could be read (revision 2, 14 November 2026); each row says
in `stimulusFrom` what was read and in `reconstruction` what was still assumed. Revision 1 rebuilt every stimulus from
the project's research notes. The benchmark constrains a model; it does not validate one. Validation is listener
data on sound effects, held out.
"""
from __future__ import annotations

import datetime
import hashlib

import numpy as np
from scipy.signal import butter, sosfilt

from .. import __version__, bs1770, ecma, zwicker
from ..model import literature
from ..calibration import P0
from ..measure import implementations

SR = 48000
RNG_SEED = 20261110
REVISION = 2


# ------------------------------------------------------------------ stimuli (sound pressure in Pa, 48 kHz)

def _amp(spl: float) -> float:
    return P0 * 10 ** (spl / 20)


def _ramp(x: np.ndarray, ms: float, linear: bool = False) -> np.ndarray:
    n = max(1, int(round(ms * 1e-3 * SR)))
    w = np.arange(n) / n if linear else 0.5 - 0.5 * np.cos(np.pi * np.arange(n) / n)
    x = x.copy()
    x[:n] *= w
    x[-n:] *= w[::-1]
    return x


def tone_burst(spl: float, seconds: float, freq: float = 1000.0, ramp_ms: float = 1.0) -> np.ndarray:
    """A tone whose plateau has this level; `seconds` is its duration between the half-amplitude points."""
    n = int(round((seconds + ramp_ms * 1e-3) * SR))
    return _ramp(np.sqrt(2) * _amp(spl) * np.sin(2 * np.pi * freq * np.arange(n) / SR), ramp_ms)


def noise(seconds: float, lo: float = 20.0, hi: float = 20000.0, pink: bool = False, seed: int = RNG_SEED) -> np.ndarray:
    """Band-limited noise with unit RMS."""
    n = int(round(seconds * SR))
    spec = np.fft.rfft(np.random.default_rng(seed).standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec[(f < lo) | (f > hi)] = 0
    if pink:
        spec[1:] /= np.sqrt(f[1:])
    x = np.fft.irfft(spec, n)
    return x / np.sqrt((x ** 2).mean())


def noise_burst(spl: float, seconds: float, ramp_ms: float = 1.0, **kw) -> np.ndarray:
    return _ramp(_amp(spl) * noise(seconds + ramp_ms * 1e-3, **kw), ramp_ms)


def level_ramp_tone(start_spl: float, end_spl: float, seconds: float = 2.0, freq: float = 1000.0) -> np.ndarray:
    n = int(round(seconds * SR))
    level = np.linspace(start_spl, end_spl, n)
    return _ramp(np.sqrt(2) * P0 * 10 ** (level / 20) * np.sin(2 * np.pi * freq * np.arange(n) / SR), 10.0)


def decaying(carrier: np.ndarray, peak_spl: float, attack_ms: float, drop_db: float) -> np.ndarray:
    """Fast attack, then an exponential decay that has fallen by drop_db at the end."""
    n = len(carrier)
    a = max(1, int(round(attack_ms * 1e-3 * SR)))
    env = np.ones(n)
    env[:a] = np.linspace(0, 1, a)
    env[a:] = 10 ** (-drop_db * np.arange(n - a) / (n - a) / 20)
    x = carrier * env
    return x / np.abs(x).max() * np.sqrt(2) * _amp(peak_spl)


def erd_tone(spl: float, erd_s: float, freq: float = 1000.0) -> np.ndarray:
    """A tone of Florentine, Buus & Poulsen: a 6.67 ms raised-cosine rise and fall around a steady part of
    erd_s - 5 ms, so that its equivalent rectangular duration is erd_s (the "5 ms" tone is the rise and fall alone)."""
    n = int(round((erd_s - 0.005 + 2 * 6.67e-3) * SR))
    return _ramp(np.sqrt(2) * _amp(spl) * np.sin(2 * np.pi * freq * np.arange(n) / SR), 6.67)


def erd_noise(spl: float, erd_s: float, seed: int = RNG_SEED) -> np.ndarray:
    """Broadband noise gated like `erd_tone`; `spl` is the level of the steady noise."""
    return _ramp(_amp(spl) * noise(erd_s - 0.005 + 2 * 6.67e-3, seed=seed), 6.67)


def linear_gated_tone(spl: float, nominal_s: float, freq: float = 5000.0, ramp_ms: float = 2.0) -> np.ndarray:
    """A tone of Buus, Florentine & Poulsen (1997): linear rise and fall of 2 ms, duration between the half-amplitude
    points (the "2 ms" tone is the rise and fall alone)."""
    n = int(round((nominal_s + ramp_ms * 1e-3) * SR))
    return _ramp(np.sqrt(2) * _amp(spl) * np.sin(2 * np.pi * freq * np.arange(n) / SR), ramp_ms, linear=True)


def beta_envelope(pt: float, s: float = 3.0, seconds: float = 0.25) -> np.ndarray:
    """The envelope family of Stecker & Hafter (2000): y = t**(z-1) * (1-t)**(w-1) on 0..1, peak 1.
    pt < 0: fast attack and slow decay; pt > 0: its time reverse; s: sharpness (3 in the paper).
    Here z = exp(s * (1/2 + arctan(pt)/pi)) and w = exp(s) / z. The paper's line for z was unreadable in the copy
    read; this form is the simplest that has the properties the paper states (symmetric at pt = 0, +pt and -pt
    time-reversed, |pt| = 1 wider and more central than |pt| = 3)."""
    z = np.exp(s * (0.5 + np.arctan(pt) / np.pi))
    w = np.exp(s) / z
    t = (np.arange(int(round(seconds * SR))) + 0.5) / int(round(seconds * SR))
    y = t ** (z - 1) * (1 - t) ** (w - 1)
    return y / y.max()


def octave_band(fc: float, spl: float, seconds: float = 2.0, seed: int = RNG_SEED) -> np.ndarray:
    """An octave band of pink noise through an 8th-order band filter (Fenton & Lee 2017), at this level."""
    lead = SR
    x = sosfilt(butter(4, [fc / np.sqrt(2), fc * np.sqrt(2)], btype="band", fs=SR, output="sos"),
                noise(seconds + 2.0, 10.0, 22000.0, pink=True, seed=seed))[lead: lead + int(round(seconds * SR))]
    return _ramp(_amp(spl) * x / np.sqrt((x ** 2).mean()), 20.0)


def segment_noise(levels_db, segment_s: float = 0.1, seed: int = RNG_SEED) -> np.ndarray:
    """White noise in contiguous segments, each at its own level (Fischenich et al. 2021; Pedersen & Ellermeier 2008)."""
    n = int(round(segment_s * SR))
    x = noise(segment_s * len(levels_db), seed=seed)
    for i, level in enumerate(levels_db):
        x[i * n:(i + 1) * n] *= _amp(level)
    return _ramp(x, 2.0)


def gap(seconds: float) -> np.ndarray:
    return np.zeros(int(round(seconds * SR)))


def train(burst: np.ndarray, period_s: float, count: int) -> np.ndarray:
    out = np.zeros(int(round(period_s * SR)) * (count - 1) + len(burst))
    for i in range(count):
        a = int(round(i * period_s * SR))
        out[a:a + len(burst)] += burst
    return out


# ------------------------------------------------------------------ measures: "raise B by how much to match A?"

LINEAR = ("peak", "rms", "integrated", "momentaryMax", "shortTermMax")
LITERATURE_FITTED = ["integration-tone-moderate", "integration-tone-high", "integration-noise-moderate", "integration-noise-high",
                     "integration-tone-30ms", "rise-fall-asymmetry", "repetition-slow", "low-frequency-band"]
ADDED_AFTER_FITTING = ["band-125", "band-250", "band-500", "band-2000", "band-4000", "band-8000"]
MODEL = ("iso532_1.max", "iso532_1.n5")


def _linear(x: np.ndarray) -> dict:
    """Level-free measures of a pressure signal (Pa read as full-scale units: only differences are used)."""
    x2 = x[:, None]
    values, _ = bs1770.measure_span(x2, bs1770.k_weight(x2, SR), SR, 0.0, len(x) / SR)
    return values


def _secant(level_fn, target: float, tol: float = 0.05, max_iter: int = 8) -> tuple[float, bool]:
    g0, l0 = 0.0, level_fn(0.0)
    if abs(l0 - target) < tol:
        return 0.0, True
    g1 = target - l0
    for _ in range(max_iter):
        l1 = level_fn(g1)
        if abs(l1 - target) < tol or g1 == g0:
            return g1, True
        slope = min(max((l1 - l0) / (g1 - g0), 0.2), 5.0)
        g0, l0, g1 = g1, l1, g1 + (target - l1) / slope
    return g1, abs(level_fn(g1) - target) < 4 * tol


def predictions(a: np.ndarray, b: np.ndarray, ecma_python: str | None, ecma_known: float | None = None) -> dict:
    out = {}
    la, lb = _linear(a), _linear(b)
    for key in LINEAR:
        out[key] = round(la[key] - lb[key], 2)
    za, zb = zwicker.Zwicker(a), zwicker.Zwicker(b)
    na = za.curve(1.0).n
    for key, stat in (("iso532_1.max", lambda n, m: n.max()),
                      ("iso532_1.n5", lambda n, m: np.percentile(n[: m.frames_signal + int(zwicker.LAG_S / zwicker.FRAME_S)], 95))):
        target = float(zwicker.sone_to_phon(stat(na, za)))
        g, ok = _secant(lambda gain: float(zwicker.sone_to_phon(stat(zb.curve(1.0, gain).n, zb))), target)
        out[key] = round(g, 2) if ok else None
    lp = literature.FITTED
    out["literature.L0"] = round(literature.matching_gain(literature.track(a, lp.shelf_db), literature.track(b, lp.shelf_db), lp), 2)
    if ecma_known is not None:
        out["ecma418_2.max"] = ecma_known
    elif ecma_python:
        def emax(sig, gain=0.0):
            r = ecma.run([sig], 10 ** (gain / 20), ecma_python, roughness=False)
            sel = (r["time"] >= 0) & (r["time"] <= len(sig) / SR + 0.1)
            return 40.0 + 10.0 * np.log2(max(float(r["loudness"][sel].max()), 1e-6))  # loudness level, doubling per 10
        try:
            target = emax(a)
            g, ok = _secant(lambda gain: emax(b, gain), target, tol=0.1, max_iter=6)
            out["ecma418_2.max"] = round(g, 2) if ok else None
        except Exception:
            out["ecma418_2.max"] = None
    return out


# ------------------------------------------------------------------ the phenomena

# Fenton & Lee (2017), Table 1: BS.1770's error per octave band (BS.1770's gain minus the listeners'), dB
FENTON_LEE_K_ERROR = {125: -3.794, 250: -1.114, 500: 3.050, 2000: 1.087, 4000: 1.182, 8000: -1.040}
# BS.1770's gain for each band against the 1 kHz band, octave bands of pink noise at equal level through the paper's
# filter order, as computed here (integrated loudness). The paper prints this value for 63 Hz only: 2.73, where this
# computation gives 3.55. The listeners' gain per band is this minus the error above, so it carries that doubt.
K_GAIN_HERE = {125: 1.63, 250: 1.03, 500: 0.80, 2000: -2.14, 4000: -3.08, 8000: -3.18}


def phenomena() -> list[dict]:
    P = []
    impact = decaying(noise(0.3, 100, 8000, seed=RNG_SEED + 7), 80.0, 1.0, 60.0)
    FL96 = ("Florentine, Buus & Poulsen (1996), JASA 99(3):1633-1644; 6 listeners, adaptive two-interval matching")
    read96 = ("abstract (journal and 1995 meeting); the tones' gating from Buus, Florentine & Poulsen (1999), which says "
              "the 1996 study used the same; the paper itself is behind a paywall and was not read")

    P.append(dict(
        id="integration-tone-moderate", kind="value", negate=True,
        title="Temporal integration, 1 kHz tone, where it is largest",
        a=erd_tone(56.0, 0.005), b=erd_tone(56.0, 0.200),
        published=(18.0, 19.0), unit="dB the 5 ms tone lies above the equally loud 200 ms tone, the 5 ms tone held at 56 dB SPL",
        source=FL96 + ": a peak of 18 to 19 dB when the 5 ms tone is about 56 dB SPL", evidence="established",
        stimulusFrom=read96,
        reconstruction="later studies of the same laboratory with a roving-level procedure found maxima of 26 to 27 dB (Buus et al. 1999)"))
    P.append(dict(
        id="integration-tone-high", kind="value", negate=True,
        title="Temporal integration, 1 kHz tone, high level",
        a=erd_tone(100.0, 0.005), b=erd_tone(100.0, 0.200),
        published=(9.0, 11.0), unit="dB the 5 ms tone lies above the equally loud 200 ms tone, the 5 ms tone held at 100 dB SPL",
        source=FL96 + ": about 10 dB near 100 dB SPL", evidence="established", stimulusFrom=read96,
        reconstruction="'about 10 dB' taken as 9 to 11; 'near 100 dB SPL' taken as the 5 ms tone's level (Buus et al. 1999 give 11 dB with the 200 ms tone at 90)"))
    P.append(dict(
        id="integration-noise-moderate", kind="value", negate=True,
        title="Temporal integration, broadband noise, where it is largest",
        a=erd_noise(76.0, 0.005, seed=RNG_SEED + 2), b=erd_noise(76.0, 0.200, seed=RNG_SEED + 1),
        published=(18.0, 19.0), unit="dB the 5 ms noise lies above the equally loud 200 ms noise, the 5 ms noise held at 76 dB SPL",
        source=FL96 + ": a peak of 18 to 19 dB when the 5 ms noise is about 76 dB SPL", evidence="established", stimulusFrom=read96,
        reconstruction="noise 20 Hz to 20 kHz, gated like the tones: the noise's bandwidth and gating were not available"))
    P.append(dict(
        id="integration-noise-high", kind="value", negate=True,
        title="Temporal integration, broadband noise, high level",
        a=erd_noise(100.0, 0.005, seed=RNG_SEED + 2), b=erd_noise(100.0, 0.200, seed=RNG_SEED + 1),
        published=(12.0, 14.0), unit="dB the 5 ms noise lies above the equally loud 200 ms noise, the 5 ms noise held at 100 dB SPL",
        source=FL96 + ": about 13 dB near 100 dB SPL", evidence="established", stimulusFrom=read96,
        reconstruction="'about 13 dB' taken as 12 to 14; bandwidth and gating as in the row above"))
    P.append(dict(
        id="integration-tone-30ms", kind="value",
        title="Temporal integration, 1 kHz tone, 30 against 200 ms",
        a=erd_tone(37.5, 0.200), b=erd_tone(37.5, 0.030),
        published=(6.0, 8.0), unit="dB the 30 ms tone must be raised to match the 200 ms tone",
        source="Buus, Florentine & Poulsen (1997), JASA 101(2):669-680, on the 1996 data: a maximum of about 7 dB", evidence="established",
        stimulusFrom="Buus et al. (1997), read in the paper, for the number; gating as in the rows above",
        reconstruction="the 200 ms tone at 37.5 dB SPL, its level when as loud as the 5 ms tone at 56 dB SPL; the paper gives no level for this maximum"))
    rising = level_ramp_tone(60.0, 75.0)
    P.append(dict(
        id="rise-fall-asymmetry", kind="value",
        title="A rising tone is louder than the same tone falling",
        a=rising, b=rising[::-1].copy(),
        published=(3.1, 5.3), unit="dB the falling tone must be raised to match the rising one",
        source="Ponsot, Susini & Meunier (2015), Atten. Percept. Psychophys. 77(3):907-920: 3.4 and 3.2 dB by matching (10 and 12 listeners), 5.3 and 3.1 dB by magnitude estimation (16 each)",
        evidence="established", stimulusFrom="the paper (publisher's page)",
        reconstruction="1 kHz, 2 s, 60 to 75 dB SPL linear in dB, 10 ms gating: one of the paper's seven ranges; the asymmetry was smaller for the ramps reaching 80 to 90 dB SPL"))
    for name, carrier in (("tone", np.sin(2 * np.pi * 330.0 * np.arange(int(0.25 * SR)) / SR)), ("noise", noise(0.25, seed=RNG_SEED + 5))):
        fs = np.sqrt(2) * _amp(80.0) * beta_envelope(-3.0) * carrier
        sf = np.sqrt(2) * _amp(80.0) * beta_envelope(+3.0) * carrier
        P.append(dict(
            id=f"decay-suppression-{name}", kind="sign", sign=-1,
            title=f"An impact-like envelope is softer than its time reverse ({name})",
            a=fs, b=sf,
            published=(-3.0, -1.0), unit="dB the slow-attack, fast-decay sound must be lowered to match the impact-like one",
            source="Stecker & Hafter (2000), JASA 107(6):3358-3368: 1 to 3 dB for one listener after impact-like standards, under 1 dB after the others; "
                   "the same sign by magnitude estimation for tones and noise (8 listeners each) and from 330 Hz to 6 kHz",
            evidence="single study; the sign is the finding, the size is weak", stimulusFrom="the paper (authors' reprint)",
            reconstruction=("250 ms, the paper's envelope family with sharpness 3 and peak-time parameter 3, "
                            + ("330 Hz tone" if name == "tone" else "white noise") + ", peak equal to a sinusoid's at 80 dB SPL; "
                            "one line of the envelope's equation was unreadable in the copy and was completed from the properties the paper states")))
    burst = decaying(noise(0.05, seed=RNG_SEED + 3), 80.0, 1.0, 40.0)
    ogura = "abstract only: the paper's file could not be fetched (the journal's site refuses automated reading)"
    P.append(dict(
        id="repetition-slow", kind="value",
        title="A slow train of impulses is as loud as one impulse",
        a=burst, b=train(burst, 4.0, 3),
        published=(-1.0, 1.0), unit="dB the train must be raised to match the single impulse (none)",
        source="Ogura, Suzuki & Sone (1991), J. Acoust. Soc. Jpn (E) 12(1):1-11: no change up to 0.2-0.7 impulses a second",
        evidence="single study", stimulusFrom=ogura,
        reconstruction="noise impulse of 50 ms, three of them 4 s apart (0.25 a second); 'as loud' taken as within 1 dB"))
    P.append(dict(
        id="repetition-fast", kind="sign", sign=-1,
        title="A fast train of impulses is louder than one impulse",
        a=burst, b=train(burst, 0.2, 10),
        published=None, unit="dB the train must be lowered to match the single impulse",
        source="Ogura, Suzuki & Sone (1991): above the critical rate loudness grows with rate",
        evidence="single study; sign only", stimulusFrom=ogura, reconstruction="the same impulse, ten of them 0.2 s apart (5 a second)"))
    fenton = "Fenton & Lee (2017), AES 143rd Convention: 13 listeners, method of adjustment, one loudspeaker at 2 m, the 1 kHz band at 75 dB"
    ref_band = octave_band(1000.0, 75.0, seed=RNG_SEED + 4)
    P.append(dict(
        id="low-frequency-band", kind="value",
        title="A 63 Hz octave band of noise against a 1 kHz band",
        a=ref_band, b=octave_band(63.0, 75.0, seed=RNG_SEED + 4),
        published=(9.0, 11.0), unit="dB the 63 Hz band must be raised to match the 1 kHz band",
        source=fenton + "; listeners gave about 9.98 dB at 63 Hz", evidence="single study", stimulusFrom="the paper (authors' preprint)",
        reconstruction="octave bands of pink noise through 8th-order filters, both at 75 dB SPL, 2 s (the paper looped them); 9.98 dB taken as 9 to 11"))
    for fc in (125, 250, 500, 2000, 4000, 8000):
        mid = K_GAIN_HERE[fc] - FENTON_LEE_K_ERROR[fc]
        P.append(dict(
            id=f"band-{fc}", kind="value",
            title=f"{'An' if fc == 8000 else 'A'} {f'{fc} Hz' if fc < 1000 else f'{fc // 1000} kHz'} octave band of noise against a 1 kHz band",
            a=ref_band, b=octave_band(float(fc), 75.0, seed=RNG_SEED + 4),
            published=(round(mid - 1.5, 1), round(mid + 1.5, 1)), unit=f"dB the {fc} Hz band must be raised to match the 1 kHz band",
            source=fenton + f"; Table 1 gives BS.1770's error for this band ({FENTON_LEE_K_ERROR[fc]:+.2f} dB)",
            evidence="single study; the value is derived", stimulusFrom="the paper (authors' preprint)",
            reconstruction=(f"the listeners' gain is derived: BS.1770's gain as computed here ({K_GAIN_HERE[fc]:+.2f} dB) minus the paper's error; "
                            "the paper's own BS.1770 value is printed for 63 Hz only and is 0.8 dB under this project's, so 1.5 dB either side is allowed")))
    base = [55.0] * 10
    early, late = list(base), list(base)
    early[0] += 5.0
    late[5] += 5.0
    P.append(dict(
        id="primacy", kind="sign", sign=1,
        title="A louder beginning counts for more than a louder middle",
        a=segment_noise(early, seed=RNG_SEED + 6), b=segment_noise(late, seed=RNG_SEED + 6),
        published=None, unit="dB the sound with the louder middle must be raised to match the one with the louder beginning",
        source="Fischenich, Hots, Verhey, Guldan & Oberfeld (2021), PLoS ONE 16(12):e0261001: for contiguous 100 ms segments the first weighs 4 to 5 times "
               "a later one, falling off over 200 to 300 ms; no primacy when the segments are 500 ms apart. Pedersen & Ellermeier (2008), JASA 123(2):963-972: "
               "the same without feedback, and flat weights for listeners given feedback",
        evidence="established; sign only", stimulusFrom="both papers (open copies)",
        reconstruction="1 s white noise in ten 100 ms segments at 55 dB SPL, 5 dB more in the first or in the sixth; the papers measured weights from random "
                       "level changes of 2 to 2.5 dB, not this contrast; with their weights it would be worth about 1 dB"))

    # contrasts nobody has measured: each measure's prediction, on record before the listening test
    tail = _amp(80.0) * 10 ** (-12 / 20) * noise(2.0, 100, 8000, seed=RNG_SEED + 8) * 10 ** (-60 * np.arange(int(2.0 * SR)) / (2.0 * SR) / 20)
    wet = np.concatenate([impact, np.zeros(len(tail) - len(impact))]) + np.concatenate([np.zeros(int(0.01 * SR)), tail[:-int(0.01 * SR)]])
    P.append(dict(
        id="open-dry-wet", kind="open", title="The same impact dry and with a 2 s reverberant tail",
        a=impact, b=wet, published=None, unit="dB the wet version would be raised (negative: lowered) to match the dry one",
        source="no listener data found (perception_and_measures.md, section 3)", evidence="open question", stimulusFrom="this project",
        reconstruction="noise impact of 0.3 s; tail 12 dB under its peak, decaying 60 dB in 2 s"))
    for spl in (60.0, 80.0):
        click = _ramp(_amp(spl) * noise(0.03, 2000, 6000, seed=RNG_SEED + 9), 2.0)
        boom_n = int(1.2 * SR)
        boom = _amp(spl) * noise(1.2, 30, 150, seed=RNG_SEED + 10) * np.exp(-np.arange(boom_n) / (0.25 * SR))
        boom[: int(0.005 * SR)] *= np.linspace(0, 1, int(0.005 * SR))
        P.append(dict(
            id=f"open-boom-click-{spl:g}", kind="open", title=f"A 30-150 Hz boom against a 2-6 kHz click, around {spl:g} dB SPL",
            a=click, b=boom, published=None, unit="dB the boom would be raised to match the click",
            source="no listener data found (perception_and_measures.md, section 4)", evidence="open question", stimulusFrom="this project",
            reconstruction="click 30 ms; boom 1.2 s with a 250 ms decay; both built from noise of the stated level"))
    return P


def _verdict(p: dict, value: float | None) -> str:
    if value is None:
        return "no value"
    if p["kind"] == "open":
        return "prediction"
    if p["kind"] == "sign":
        if abs(value) < 0.5:
            return "no effect"
        return "agrees" if np.sign(value) == p["sign"] else "opposite"
    lo, hi = p["published"]
    miss = max(lo - value, value - hi, 0.0)
    return "agrees" if miss <= 1.0 else ("near" if miss <= 3.0 else "off")


def _miss(p: dict, value: float | None):
    if value is None or p["kind"] != "value":
        return None
    lo, hi = p["published"]
    return round(value - hi if value > hi else (value - lo if value < lo else 0.0), 2)


def _hash(p: dict) -> str:
    h = hashlib.sha1()
    for x in (p["a"], p["b"]):
        h.update(np.ascontiguousarray(x, dtype=np.float64).tobytes())
    return h.hexdigest()[:16]


def run(levels=None, ecma_python: str | None = None, ecma_from: dict | None = None) -> dict:
    """`ecma_from`: an earlier listener-phenomena document whose ECMA-418-2 values are kept for the rows whose two
    sounds are unchanged (they take most of the run's time and do not depend on anything else here)."""
    rows = []
    known = {}
    if ecma_from and ecma_from.get("generator", {}).get("version") == __version__:
        known = {r["id"]: (r.get("stimulusHash"), r["predictions"].get("ecma418_2.max")) for r in ecma_from["phenomena"]}
    reused = 0
    for p in phenomena():
        sign = -1.0 if p.get("negate") else 1.0
        digest = _hash(p)
        kept = known.get(p["id"], (None, None))
        ecma_known = sign * kept[1] if kept[0] == digest and kept[1] is not None else None
        reused += ecma_known is not None
        pred = predictions(p["a"], p["b"], ecma_python, ecma_known)
        if p.get("negate"):
            pred = {k: (None if v is None else round(-v, 2)) for k, v in pred.items()}
        rows.append({
            "id": p["id"], "kind": p["kind"], "title": p["title"], "question": p["unit"],
            "published": list(p["published"]) if p["published"] else None,
            "expectedSign": p.get("sign"), "source": p["source"], "evidence": p["evidence"],
            "stimulusFrom": p["stimulusFrom"], "reconstruction": p["reconstruction"], "stimulusHash": digest,
            "predictions": pred,
            "miss": {k: _miss(p, v) for k, v in pred.items()},
            "verdicts": {k: _verdict(p, v) for k, v in pred.items()},
        })
    measures = list(rows[0]["predictions"])
    for r in rows:
        for m in measures:
            r["predictions"].setdefault(m, None), r["miss"].setdefault(m, None), r["verdicts"].setdefault(m, "no value")
    tested = [r for r in rows if r["kind"] != "open"]
    score = {m: {"agrees": sum(1 for r in tested if r["verdicts"][m] == "agrees"),
                 "near": sum(1 for r in tested if r["verdicts"][m] == "near"),
                 "of": len(tested)} for m in measures}
    held = [r["id"] for r in tested if r["id"] not in LITERATURE_FITTED and r["id"] != "primacy"]
    return {
        "format": "listener-phenomena", "version": 1, "revision": REVISION,
        "generator": {"name": "listener", "version": __version__},
        "created": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "implementations": implementations(ecma_python or ("reused" if reused else None)),
        **({"ecmaReusedFrom": ecma_from.get("created"), "ecmaReusedRows": reused} if reused else {}),
        "rule": "Each value: dB by which a measure would raise sound B to make it as loud as sound A, or the level difference the row's question names. 'agrees': within 1 dB of the published range (or the right sign, at least 0.5 dB); 'near': within 3 dB; 'off': further; 'no effect': under 0.5 dB where a sign is expected; 'opposite': the wrong sign.",
        "caution": "Each row says what was read of its paper and what was assumed. The published ranges come from small panels, and for the largest temporal integration later studies of the same laboratory found more. This constrains a model. It does not validate one for sound effects.",
        "measures": measures, "score": score,
        "literatureModel": {
            "note": "literature.L0 was set from the rows in 'fitted'; only the rows in 'heldOut' test it; those in 'addedAfterFitting' entered the benchmark after the model was fitted and were never fitted; 'notModelled' it is expected to fail",
            "fitted": LITERATURE_FITTED, "heldOut": held, "addedAfterFitting": ADDED_AFTER_FITTING,
            "notModelled": ["primacy"],
            "scoreHeldOut": {m: {"agrees": sum(1 for r in tested if r["id"] in held and r["verdicts"][m] == "agrees"),
                                 "near": sum(1 for r in tested if r["id"] in held and r["verdicts"][m] == "near"), "of": len(held)}
                             for m in measures},
        },
        "phenomena": rows,
    }


def report_markdown(doc: dict) -> str:
    ms = doc["measures"]
    short = {"peak": "Peak", "rms": "RMS", "integrated": "LUFS-I", "momentaryMax": "Max M", "shortTermMax": "Max S",
             "iso532_1.max": "ISO 532-1 Nmax", "iso532_1.n5": "ISO 532-1 N5", "ecma418_2.max": "ECMA-418-2 max",
             "literature.L0": "Literature model L0"}
    mark = {"agrees": "", "near": " ~", "off": " ✗", "no effect": " ✗ (none)", "opposite": " ✗ (opposite)", "prediction": "", "no value": ""}
    L = ["# Published loudness phenomena against the measures\n", doc["rule"] + "\n", doc["caution"] + "\n",
         "| Phenomenon | Listeners | " + " | ".join(short.get(m, m) for m in ms) + " |", "|---|---|" + "---|" * len(ms)]
    for r in doc["phenomena"]:
        if r["kind"] == "open":
            continue
        pub = (f"{r['published'][0]:g} to {r['published'][1]:g}" if r["published"] else "") if r["kind"] == "value" else \
              (("positive" if r["expectedSign"] > 0 else "negative") + (f" ({r['published'][0]:g} to {r['published'][1]:g})" if r["published"] else ""))
        fitted = r["id"] in doc.get("literatureModel", {}).get("fitted", [])
        L.append(f"| {r['title']}{' †' if fitted else ''} | {pub} | " + " | ".join(
            ("–" if r["predictions"][m] is None else f"{r['predictions'][m]:+.1f}") + mark[r["verdicts"][m]] for m in ms) + " |")
    L.append("| **Agrees (near)** | | " + " | ".join(f"**{doc['score'][m]['agrees']}** ({doc['score'][m]['near']}) of {doc['score'][m]['of']}" for m in ms) + " |")
    L.append("\n✗: more than 3 dB from the published range, no effect where one is expected, or the wrong sign. ~: within 3 dB.\n")
    if "literatureModel" in doc:
        lm = doc["literatureModel"]
        L.append("†: a result the literature model was set from. For that model only the rows without † are a test, and it has no onset weighting, so the last row is expected to fail.\n")
        if "scoreHeldOut" in lm and isinstance(next(iter(lm["scoreHeldOut"].values())), dict):
            L.append("On the rows without † (the last row apart), agrees (near) of " + str(next(iter(lm["scoreHeldOut"].values()))["of"]) + ": "
                     + "; ".join(f"{short.get(m, m)} {v['agrees']} ({v['near']})" for m, v in lm["scoreHeldOut"].items()) + ".\n")
    L.append("## Contrasts nobody has measured: the predictions on record\n")
    L.append("| Contrast | " + " | ".join(short.get(m, m) for m in ms) + " | Spread |")
    L.append("|---|" + "---|" * (len(ms) + 1))
    for r in doc["phenomena"]:
        if r["kind"] != "open":
            continue
        vals = [v for v in r["predictions"].values() if v is not None]
        L.append(f"| {r['title']} | " + " | ".join("–" if r["predictions"][m] is None else f"{r['predictions'][m]:+.1f}" for m in ms)
                 + f" | {max(vals) - min(vals):.1f} |")
    L.append("\n## Sources and what was assumed\n")
    for r in doc["phenomena"]:
        L.append(f"- **{r['title']}.** {r['question']}. {r['source']} [{r['evidence']}]. Read: {r.get('stimulusFrom', 'the research notes')}. Assumed or noted: {r['reconstruction']}.")
    return "\n".join(L) + "\n"
