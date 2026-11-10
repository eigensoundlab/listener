# SPDX-License-Identifier: Apache-2.0
"""EBU Tech 3341 (v4, 2023) and Tech 3342 (v4, 2023) minimum-requirement tests, synthesised from the documents' tables.

The EBU distributes these signals as files (EBU terms of use). Every case that the documents define by a formula is
built here from that formula, so the suite runs without the download. The four cases that are programme recordings
(Tech 3341 cases 7 and 8, Tech 3342 cases 5 and 6) need the EBU's files: `--ebu <folder>`.
"""
from __future__ import annotations

import os

import numpy as np
from scipy.signal import firwin, lfilter

from .. import bs1770
from ..audio import load

SOURCE_3341 = "EBU Tech 3341 v4 (2023), Table 1, synthesised"
SOURCE_3342 = "EBU Tech 3342 v4 (2023), Table 1, synthesised"


def tone(level_dbfs: float, seconds: float, sr: int, channels: int = 2, freq: float = 1000.0) -> np.ndarray:
    """A sine with this per-channel peak level, the same phase in every channel."""
    t = np.arange(int(round(seconds * sr))) / sr
    s = 10 ** (level_dbfs / 20) * np.sin(2 * np.pi * freq * t)
    return np.repeat(s[:, None], channels, axis=1)


def silence(seconds: float, sr: int, channels: int = 2) -> np.ndarray:
    return np.zeros((int(round(seconds * sr)), channels))


def sequence(parts, sr):
    return np.vstack([tone(lv, sec, sr) if lv is not None else silence(sec, sr) for lv, sec in parts])


def _case(suite, case, text, expected, tol, measured, source, unit="LUFS"):
    lo, hi = (tol if isinstance(tol, tuple) else (-tol, tol))
    measured = [measured] if np.isscalar(measured) else list(measured)
    expected_l = [expected] * len(measured) if np.isscalar(expected) else list(expected)
    dev = [m - e for m, e in zip(measured, expected_l)]
    ok = all(lo - 1e-9 <= d <= hi + 1e-9 for d in dev)
    worst = max(dev, key=abs) if dev else float("nan")
    return {"suite": suite, "case": case, "signal": text, "expected": expected, "tolerance": [lo, hi], "unit": unit,
            "measured": round(float(measured[0]), 3) if len(measured) == 1 else [round(float(m), 3) for m in measured],
            "worstDeviation": round(float(worst), 3), "pass": bool(ok), "source": source}


def _m(x, sr):
    return bs1770.window_loudness(bs1770.k_weight(x, sr), sr, bs1770.MOMENTARY_S)


def _s(x, sr):
    return bs1770.window_loudness(bs1770.k_weight(x, sr), sr, bs1770.SHORT_TERM_S)


def _true_peak_special(sr: int, offset: int) -> np.ndarray:
    """Cases 20-23: an fs/6 sine of amplitude 0.5 holding one period of an fs/4 sine of amplitude 1, made at 4 fs."""
    hi = 4 * sr
    n = int(0.5 * hi)
    t = np.arange(n)
    x = 0.5 * np.sin(2 * np.pi * t / 24.0)          # fs/6 at 4 fs: 24 samples a period
    start = 24 * (n // 48)                            # a zero crossing going up
    x[start:start + 16] = np.sin(2 * np.pi * np.arange(16) / 16.0)  # one period of fs/4: 16 samples
    x[start + 16:] = 0.5 * np.sin(2 * np.pi * np.arange(n - start - 16) / 24.0)  # continues in phase
    taps = firwin(255, 0.25 * 0.98)                   # anti-alias low-pass before taking every fourth sample
    y = lfilter(taps, 1.0, x)[127:]                   # compensate the delay
    y = y[offset::4]
    fade = int(0.01 * sr)
    y[:fade] *= np.linspace(0, 1, fade)
    y[-fade:] *= np.linspace(1, 0, fade)
    return np.repeat(y[:, None], 2, axis=1)


def cases(sr: int = 48000) -> list[dict]:
    out = []
    S1, S2 = SOURCE_3341, SOURCE_3342

    for case, level in ((1, -23.0), (2, -33.0)):
        x = tone(level, 20, sr)
        out.append(_case("tech3341", case, f"stereo 1 kHz sine, {level:g} dBFS, 20 s",
                         level, 0.1, [_m(x, sr).max(), _s(x, sr).max(), bs1770.integrated(x, sr)], S1))
    seqs = {
        3: [(-36, 10), (-23, 60), (-36, 10)],
        4: [(-72, 10), (-36, 10), (-23, 60), (-36, 10), (-72, 10)],
        5: [(-26, 20), (-20, 20.1), (-26, 20)],
    }
    for case, parts in seqs.items():
        x = sequence(parts, sr)
        out.append(_case("tech3341", case, "; ".join(f"{s:g} s at {l:g} dBFS" for l, s in parts),
                         -23.0, 0.1, bs1770.integrated(x, sr), S1))
    t = np.arange(20 * sr) / sr
    five = np.stack([10 ** (lv / 20) * np.sin(2 * np.pi * 1000 * t) for lv in (-28, -28, -24, -30, -30)], axis=1)
    out.append(_case("tech3341", 6, "5.0 sine: L, R -28; C -24; Ls, Rs -30 dBFS, 20 s", -23.0, 0.1,
                     bs1770.integrated(five, sr), S1))

    x = sequence([(-20, 1.34), (-30, 1.66)] * 5, sr)
    s = _s(x, sr)  # windows ending at 3 s or later: every one of them
    out.append(_case("tech3341", 9, "(1.34 s at -20; 1.66 s at -30 dBFS) x 5: S constant after 3 s", -23.0, 0.1,
                     [s.min(), s.max()], S1))
    vals = [_s(sequence([(None, i * 0.15), (-23, 3), (None, 1)], sr), sr).max() for i in range(20)]
    out.append(_case("tech3341", 10, "20 segments: i x 0.15 s silence, 3 s at -23 dBFS, 1 s silence: Max S each",
                     -23.0, 0.1, vals, S1))
    vals = [_s(sequence([(None, i * 0.15), (-38 + i, 3), (None, 3 - i * 0.15)], sr), sr).max() for i in range(20)]
    out.append(_case("tech3341", 11, "20 tones of 3 s at -38 ... -19 dBFS: Max S each",
                     [-38.0 + i for i in range(20)], 0.1, vals, S1))

    x = sequence([(-20, 0.18), (-30, 0.22)] * 25, sr)
    m = _m(x, sr)
    out.append(_case("tech3341", 12, "(0.18 s at -20; 0.22 s at -30 dBFS) x 25: M constant after 1 s", -23.0, 0.1,
                     [m.min(), m.max()], S1))
    vals = [_m(sequence([(None, i * 0.02), (-23, 0.4), (None, 1)], sr), sr).max() for i in range(20)]
    out.append(_case("tech3341", 13, "20 segments: i x 20 ms silence, 0.4 s at -23 dBFS, 1 s silence: Max M each",
                     -23.0, 0.1, vals, S1))
    vals = [_m(sequence([(None, i * 0.02), (-38 + i, 0.4), (None, 0.4 - i * 0.02)], sr), sr).max() for i in range(20)]
    out.append(_case("tech3341", 14, "20 tones of 0.4 s at -38 ... -19 dBFS: Max M each",
                     [-38.0 + i for i in range(20)], 0.1, vals, S1))

    def tp_sine(div, amp, phase_deg):
        n = np.arange(int(0.5 * sr))
        y = amp * np.sin(2 * np.pi * n / div + np.deg2rad(phase_deg))
        fade = int(0.01 * sr)
        y[:fade] *= np.linspace(0, 1, fade)
        y[-fade:] *= np.linspace(1, 0, fade)
        return np.repeat(y[:, None], 2, axis=1)

    for case, div, amp, ph, exp in ((15, 4, 0.5, 0.0, -6.0), (16, 4, 0.5, 45.0, -6.0), (17, 6, 0.5, 60.0, -6.0),
                                    (18, 8, 0.5, 67.5, -6.0), (19, 4, 1.41, 45.0, 3.0)):
        out.append(_case("tech3341", case, f"sine at fs/{div}, amplitude {amp:g}, phase {ph:g} deg", exp, (-0.4, 0.2),
                         bs1770.true_peak_db(tp_sine(div, amp, ph)), S1, "dBTP"))
    for case, off in ((20, 0), (21, 1), (22, 2), (23, 3)):
        out.append(_case("tech3341", case, f"fs/6 sine holding one period of an fs/4 sine, made at 4 fs, offset {off}",
                         0.0, (-0.4, 0.2), bs1770.true_peak_db(_true_peak_special(sr, off)), S1, "dBTP"))

    for case, levels, exp in ((1, (-20, -30), 10.0), (2, (-20, -15), 5.0), (3, (-40, -20), 20.0),
                              (4, (-50, -35, -20, -35, -50), 15.0)):
        x = sequence([(lv, 20) for lv in levels], sr)
        out.append(_case("tech3342", case, "1 kHz sine, 20 s each at " + ", ".join(f"{l:g}" for l in levels) + " dBFS",
                         exp, 1.0, bs1770.loudness_range(x, sr), S2, "LU"))
    return out


PROGRAMME = {  # the EBU's file names for the cases that are recordings
    ("tech3341", 7): ("seq-3341-7_seq-3342-5-24bit.wav", "integrated", -23.0, 0.1),
    ("tech3341", 8): ("seq-3341-2011-8_seq-3342-6-24bit-v02.wav", "integrated", -23.0, 0.1),
    ("tech3342", 5): ("seq-3341-7_seq-3342-5-24bit.wav", "lra", 5.0, 1.0),
    ("tech3342", 6): ("seq-3341-2011-8_seq-3342-6-24bit-v02.wav", "lra", 15.0, 1.0),
}


def programme_cases(folder: str | None) -> list[dict]:
    out = []
    for (suite, case), (name, what, exp, tol) in PROGRAMME.items():
        path = os.path.join(folder, name) if folder else None
        if not path or not os.path.isfile(path):
            out.append({"suite": suite, "case": case, "signal": f"programme recording ({name})", "expected": exp,
                        "tolerance": [-tol, tol], "pass": None,
                        "skipped": "needs the EBU loudness test set: listener conform --ebu <folder>"})
            continue
        x, sr, _ = load(path)
        val = bs1770.integrated(x, sr) if what == "integrated" else bs1770.loudness_range(x, sr)
        out.append(_case(suite, case, f"programme recording ({name})", exp, tol, val, "EBU loudness test set",
                         "LUFS" if what == "integrated" else "LU"))
    return out


def fixture(sr: int = 48000) -> dict:
    """The synthesised cases as recipes another implementation can build and check (Playhead's tests)."""
    return {
        "source": "EBU Tech 3341 v4 and Tech 3342 v4, Table 1 of each; signals are 1 kHz sines, same phase in both channels, levels are per-channel peak levels in dBFS",
        "sampleRate": sr,
        "integrated": [
            {"case": 1, "parts": [[-23, 20]], "expected": -23.0, "tolerance": 0.1},
            {"case": 2, "parts": [[-33, 20]], "expected": -33.0, "tolerance": 0.1},
            {"case": 3, "parts": [[-36, 10], [-23, 60], [-36, 10]], "expected": -23.0, "tolerance": 0.1},
            {"case": 4, "parts": [[-72, 10], [-36, 10], [-23, 60], [-36, 10], [-72, 10]], "expected": -23.0, "tolerance": 0.1},
            {"case": 5, "parts": [[-26, 20], [-20, 20.1], [-26, 20]], "expected": -23.0, "tolerance": 0.1},
        ],
        "shortTerm": [
            {"case": 9, "parts": [[-20, 1.34], [-30, 1.66]], "repeat": 5, "expected": -23.0, "tolerance": 0.1, "rule": "every 3 s window"},
            {"case": 10, "segments": 20, "silenceBefore": "i * 0.15", "tone": [-23, 3], "silenceAfter": 1, "expected": -23.0, "tolerance": 0.1, "rule": "Max S of each segment"},
            {"case": 11, "segments": 20, "silenceBefore": "i * 0.15", "tone": ["-38 + i", 3], "silenceAfter": "3 - i * 0.15", "expected": "-38 + i", "tolerance": 0.1, "rule": "Max S of each segment"},
        ],
        "momentary": [
            {"case": 12, "parts": [[-20, 0.18], [-30, 0.22]], "repeat": 25, "expected": -23.0, "tolerance": 0.1, "rule": "every 0.4 s window"},
            {"case": 13, "segments": 20, "silenceBefore": "i * 0.02", "tone": [-23, 0.4], "silenceAfter": 1, "expected": -23.0, "tolerance": 0.1, "rule": "Max M of each segment"},
            {"case": 14, "segments": 20, "silenceBefore": "i * 0.02", "tone": ["-38 + i", 0.4], "silenceAfter": "0.4 - i * 0.02", "expected": "-38 + i", "tolerance": 0.1, "rule": "Max M of each segment"},
        ],
        "truePeak": [
            {"case": 15, "period": 4, "amplitude": 0.5, "phaseDeg": 0, "expected": -6.0, "tolerance": [-0.4, 0.2]},
            {"case": 16, "period": 4, "amplitude": 0.5, "phaseDeg": 45, "expected": -6.0, "tolerance": [-0.4, 0.2]},
            {"case": 17, "period": 6, "amplitude": 0.5, "phaseDeg": 60, "expected": -6.0, "tolerance": [-0.4, 0.2]},
            {"case": 18, "period": 8, "amplitude": 0.5, "phaseDeg": 67.5, "expected": -6.0, "tolerance": [-0.4, 0.2]},
            {"case": 19, "period": 4, "amplitude": 1.41, "phaseDeg": 45, "expected": 3.0, "tolerance": [-0.4, 0.2]},
        ],
        "loudnessRange": [
            {"case": 1, "parts": [[-20, 20], [-30, 20]], "expected": 10, "tolerance": 1},
            {"case": 2, "parts": [[-20, 20], [-15, 20]], "expected": 5, "tolerance": 1},
            {"case": 3, "parts": [[-40, 20], [-20, 20]], "expected": 20, "tolerance": 1},
            {"case": 4, "parts": [[-50, 20], [-35, 20], [-20, 20], [-35, 20], [-50, 20]], "expected": 15, "tolerance": 1},
        ],
        "needEbuFiles": ["Tech 3341 cases 7, 8, 20-23 as distributed", "Tech 3342 cases 5, 6"],
    }
