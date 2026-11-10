# SPDX-License-Identifier: Apache-2.0
"""ITU-R BS.1770-5 / EBU Tech 3341 and 3342 measures, per file and per span.

The K-weighting filter and the loudness range are pyloudnorm's. This module adds the sliding momentary (0.4 s) and
short-term (3 s) windows, their maxima, the true peak, the gating of integrated loudness on complete blocks only (see
`integrated`), and rules for spans shorter than a window. Those rules are the ones Playhead uses (docs/LEVELS.md), so the two can be
compared number for number:

- a span shorter than a window counts as the window with silence around it, as a meter shows an isolated sound;
- a span under 0.4 s has no gating block: its "integrated" value is its own mean, and the output says so.
"""
from __future__ import annotations

import warnings

import numpy as np
import pyloudnorm as pyln
from scipy.signal import resample_poly

MOMENTARY_S = 0.4
SHORT_TERM_S = 3.0
HOP_S = 0.01
OFFSET_DB = -0.691
FLOOR = 1e-12

# BS.1770 channel weights for L, R, C, Ls, Rs. A sixth channel in WAV order (L R C LFE Ls Rs) is the LFE: left out.
_SURROUND_GAINS = (1.0, 1.0, 1.0, 1.41, 1.41)


def channel_gains(n_channels: int) -> np.ndarray:
    if n_channels <= 3:
        return np.ones(n_channels)
    if n_channels == 5:
        return np.array(_SURROUND_GAINS)
    if n_channels == 6:
        return np.array([1.0, 1.0, 1.0, 0.0, 1.41, 1.41])
    return np.ones(n_channels)


def k_weight(x: np.ndarray, sr: int) -> np.ndarray:
    """K-weighted copy of x (frames, channels), using pyloudnorm's filter design for any sample rate."""
    meter = pyln.Meter(sr)
    y = np.array(x, dtype=np.float64, copy=True)
    for f in meter._filters.values():  # high shelf, then high pass
        for ch in range(y.shape[1]):
            y[:, ch] = f.apply_filter(y[:, ch])
    return y


def _db(mean_square_sum: np.ndarray | float):
    return OFFSET_DB + 10.0 * np.log10(np.maximum(mean_square_sum, FLOOR))


def window_loudness(ky: np.ndarray, sr: int, window_s: float, hop_s: float = HOP_S) -> np.ndarray:
    """Ungated loudness (LUFS) of every sliding rectangular window; the signal is padded to one window if shorter."""
    w = int(round(window_s * sr))
    h = max(1, int(round(hop_s * sr)))
    g = channel_gains(ky.shape[1])
    p = (ky ** 2) @ g  # weighted sum of the channels' power, per sample
    if p.shape[0] < w:
        p = np.concatenate([p, np.zeros(w - p.shape[0])])
    c = np.concatenate([[0.0], np.cumsum(p)])
    starts = np.arange(0, p.shape[0] - w + 1, h)
    return _db((c[starts + w] - c[starts]) / w)


def mean_loudness(ky: np.ndarray) -> float:
    """Ungated loudness of a whole (K-weighted) span."""
    g = channel_gains(ky.shape[1])
    return float(_db(float(((ky ** 2).mean(axis=0) * g).sum())))


def true_peak_db(x: np.ndarray, oversample: int = 4) -> float:
    """Maximum true peak in dBTP by 4x polyphase oversampling (BS.1770 Annex 2 asks for at least 4x at 48 kHz)."""
    if x.shape[0] < 8:
        return float(20 * np.log10(max(np.abs(x).max(), FLOOR)))
    y = resample_poly(x, oversample, 1, axis=0)
    return float(20 * np.log10(max(np.abs(y).max(), np.abs(x).max(), FLOOR)))


def integrated(x: np.ndarray, sr: int, ky: np.ndarray | None = None) -> float:
    """Gated integrated loudness, BS.1770-5: 0.4 s blocks every 0.1 s, gates at -70 LUFS and 10 LU under the rest.

    Only complete blocks count, as the Recommendation says. pyloudnorm 0.2.0 rounds the number of blocks instead of
    rounding it down, so on a file a little over 0.4 s it adds a block that runs past the end and reads up to 2 dB
    low (tests/test_bs1770.py); on long files the two agree. The span must be at least 0.4 s long.
    """
    if ky is None:
        ky = k_weight(x, sr)
    w, h = int(round(MOMENTARY_S * sr)), int(round(0.1 * sr))
    p = (ky ** 2) @ channel_gains(ky.shape[1])
    if p.shape[0] < w:
        raise ValueError("integrated loudness needs at least 0.4 s")
    c = np.concatenate([[0.0], np.cumsum(p)])
    starts = np.arange(0, p.shape[0] - w + 1, h)
    z = (c[starts + w] - c[starts]) / w
    loud = _db(z)
    keep = loud >= -70.0
    if not keep.any():
        return float("-inf")
    relative = _db(z[keep].mean()) - 10.0
    keep &= loud > relative
    return float(_db(z[keep].mean()))


def loudness_range(x: np.ndarray, sr: int) -> float | None:
    """EBU Tech 3342 loudness range (pyloudnorm). Needs more than 3 s; Tech 3342 warns that it misleads on short items."""
    if x.shape[0] < int(3.1 * sr):
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            return float(pyln.Meter(sr).loudness_range(x if x.shape[1] > 1 else x[:, 0]))
        except Exception:
            return None


def measure_span(x: np.ndarray, ky: np.ndarray, sr: int, start: float, end: float) -> tuple[dict, list[str]]:
    """Level-free measures of x[start:end]. ky is the K-weighted whole file, so a span keeps the filter's history."""
    a = max(0, int(round(start * sr)))
    b = min(x.shape[0], max(a + 1, int(round(end * sr))))
    seg, kseg = x[a:b], ky[a:b]
    dur = (b - a) / sr
    notes: list[str] = []
    out = {
        "peak": round(float(20 * np.log10(max(np.abs(seg).max(), FLOOR))), 2),
        "rms": round(float(10 * np.log10(max(float((seg ** 2).mean()), FLOOR))), 2),
        "momentaryMax": round(float(window_loudness(kseg, sr, MOMENTARY_S).max()), 2),
        "shortTermMax": round(float(window_loudness(kseg, sr, SHORT_TERM_S).max()), 2),
    }
    if dur >= MOMENTARY_S:
        val = integrated(seg, sr, kseg)
        if not np.isfinite(val):  # everything under the absolute gate
            val = mean_loudness(kseg)
            notes.append("integrated-ungated")
        out["integrated"] = round(val, 2)
    else:
        out["integrated"] = round(mean_loudness(kseg), 2)
        notes.append("integrated-single-block")
    if dur < MOMENTARY_S:
        notes.append("momentary-padded")
    if dur < SHORT_TERM_S:
        notes.append("short-term-padded")
    return out, notes
