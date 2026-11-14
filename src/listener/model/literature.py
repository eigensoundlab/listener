# SPDX-License-Identifier: Apache-2.0
"""An event loudness model set from published listener results (version L0).

It answers one question for one sound at a known sound pressure: its event loudness level in dB, the level of a
steady 1 kHz tone that would be as loud. Two sounds with the same value are predicted to be equally loud, so the
difference of two values, solved for gain, is a listener's adjustment.

    pressure -> K-weighting (+ low shelf) -> level every 0.5 ms
             -> decay suppression: what lies under the sound's running maximum counts for less
             -> loudness of each moment, by a loudness function that is flattest at moderate levels
             -> integration over duration in the loudness domain (a window that saturates smoothly)
             -> one value: its maximum

Where each part comes from is in docs/LITERATURE_SPLIT.md, which also says which published results set the four
fitted parameters and which were kept to test the outcome. docs/LITERATURE_MODEL.md has the results.

Domain: tones and noises of 2 ms to a few seconds in published experiments, 20 to 100 dB SPL. It has not met a
listener's judgement of a sound effect. It is not a model of the ear: one K-weighted level stands for the whole
spectrum, so there is no masking and no loudness summation across frequency, and the low-frequency shelf holds near
75 dB SPL only.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from scipy.signal import lfilter

from .. import bs1770
from ..calibration import P0

SR = 48000
RATE = 2000.0            # level track, values a second
SMOOTH_S = 0.002         # power is averaged over 2 ms before it becomes a level
SLOW_S = 0.05            # decay suppression looks at the level averaged over 50 ms
SHELF_HZ = 120.0
KERNEL_S = 3.0
BARK_EDGES = np.array([20, 100, 200, 300, 400, 510, 630, 770, 920, 1080, 1270, 1480, 1720, 2000, 2320, 2700, 3150,
                       3700, 4400, 5300, 6400, 7700, 9500, 12000, 15500], dtype=float)

# The "inflected exponential" loudness function for a 1 kHz tone (Buus & Florentine): log10(sone) as a polynomial in
# dB SPL. The coefficients are as this project's session recalled them; the paper itself was not opened. Three checks
# against sources that were: 1.000 sone at 40 dB SPL; a local exponent (re intensity) of 0.25 at 56 dB SPL and 0.41 at
# 100 dB SPL, where Buus, Florentine & Poulsen (1997) give about 0.25 and 0.43 for 1 kHz.
_INEX = (1.7058e-9, -6.587e-7, 9.7515e-5, -6.6964e-3, 0.2367, -3.4831)
_LEVELS = np.arange(-30.0, 130.01, 0.05)


def _log_sone(level: np.ndarray, kind: str) -> np.ndarray:
    level = np.clip(level, -30.0, 130.0)
    if kind == "inex":
        return np.polyval(_INEX, level)
    if kind == "power":                      # Stevens: loudness doubles every 10 dB
        return 0.030103 * (level - 40.0)
    raise ValueError(kind)


_TABLE = {k: _log_sone(_LEVELS, k) for k in ("inex", "power")}


def _level_of(log_sone: float, kind: str) -> float:
    return float(np.interp(log_sone, _TABLE[kind], _LEVELS))


@dataclass(frozen=True)
class Params:
    beta: float = 0.40       # loudness grows with duration T as (T / (T + t_half))**beta   (fitted)
    t_half: float = 0.08     # seconds                                                        (fitted)
    kappa: float = 0.0       # dB taken off per dB under the running maximum                  (fitted)
    q: float = 0.0           # 0: the maximum. Above 1: a mean that favours louder moments (tried, dropped)
    onset: float = 0.0       # extra weight of the beginning: off in L0, see docs/LITERATURE_MODEL.md
    tau_onset: float = 0.25  # its decay, seconds (Fischenich et al. 2021: 0.2 to 0.3 s, weight 4 to 5 times)
    shelf_db: float = 0.0    # low shelf under 120 Hz on top of K-weighting       (fitted)
    loudness: str = "inex"   # "inex" or "power"
    bands: bool = False      # True: loudness formed per critical band and summed (tried: fits worse, see the report)


@dataclass
class Track:
    """What does not change with gain: the level track at 0 dB gain and the band spread."""
    level: np.ndarray        # dB SPL-like (K-weighted), every 0.5 ms, with silence after the sound
    band_db: np.ndarray      # each critical band's share of the sound's power, in dB (bands under -50 dB left out)


def _low_shelf(x: np.ndarray, gain_db: float) -> np.ndarray:
    if abs(gain_db) < 1e-9:
        return x
    a_lin = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * SHELF_HZ / SR
    alpha = np.sin(w0) / 2 * np.sqrt(2.0)
    cos, sq = np.cos(w0), 2 * np.sqrt(a_lin) * alpha
    b = a_lin * np.array([(a_lin + 1) - (a_lin - 1) * cos + sq, 2 * ((a_lin - 1) - (a_lin + 1) * cos), (a_lin + 1) - (a_lin - 1) * cos - sq])
    a = np.array([(a_lin + 1) + (a_lin - 1) * cos + sq, -2 * ((a_lin - 1) + (a_lin + 1) * cos), (a_lin + 1) + (a_lin - 1) * cos - sq])
    return lfilter(b / a[0], a / a[0], x)


def track(pressure: np.ndarray, shelf_db: float = 0.0, tail_s: float = 0.3) -> Track:
    """Level track and band spread of a sound given as pressure in Pa at 48 kHz (one ear signal)."""
    x = np.concatenate([np.asarray(pressure, dtype=float), np.zeros(int(tail_s * SR))])
    k = _low_shelf(bs1770.k_weight(x[:, None], SR)[:, 0], shelf_db)
    hop = int(SR / RATE)
    n = len(k) // hop
    power = (k[: n * hop] ** 2).reshape(n, hop).mean(axis=1)
    w = max(1, int(round(SMOOTH_S * RATE)))
    power = np.convolve(power, np.ones(w) / w)[: n]
    level = 10 * np.log10(np.maximum(power, 1e-20) / P0 ** 2) + bs1770.OFFSET_DB
    spec = np.abs(np.fft.rfft(k)) ** 2
    f = np.fft.rfftfreq(len(k), 1 / SR)
    band = np.array([spec[(f >= lo) & (f < hi)].sum() for lo, hi in zip(BARK_EDGES[:-1], BARK_EDGES[1:])])
    if band.sum() <= 0:
        return Track(level, np.zeros(1))
    share = band / band.sum()
    return Track(level, 10 * np.log10(share[share > 1e-5]))


def _kernel(p: Params) -> np.ndarray:
    """Weights of the past in the loudness integrator: their sum over a duration T is (T / (T + t_half))**beta,
    so loudness grows fast with duration at first and ever more slowly, without a corner. Cut at 3 s."""
    edges = np.arange(0, int(round(KERNEL_S * RATE)) + 1) / RATE
    grown = (edges / (edges + p.t_half)) ** p.beta
    return np.diff(grown) / grown[-1]


def event_level(tr: Track, p: Params, gain_db: float = 0.0, parts: bool = False):
    """Event loudness level in dB of a sound's track at a gain."""
    level = tr.level + gain_db
    if p.kappa > 0:
        w = max(1, int(round(SLOW_S * RATE)))
        slow = 10 * np.log10(np.maximum(np.convolve(10 ** (level / 10), np.ones(w) / w)[: len(level)], 1e-30))
        under = np.maximum(np.maximum.accumulate(slow) - slow, 0.0)
        level = level - p.kappa * under
    shares = tr.band_db if p.bands else np.zeros(1)
    moment = np.zeros(len(level))
    for d in shares:     # the sound's spectrum is taken as constant over the event
        moment += np.where(level + d > -25.0, 10 ** _log_sone(level + d, p.loudness), 0.0)
    integrated = np.convolve(moment, _kernel(p))[: len(moment)]
    start = int(np.argmax(tr.level >= tr.level.max() - 30.0))
    t = (np.arange(len(integrated)) - start) / RATE
    weight = 1.0 + p.onset * np.exp(-np.maximum(t, 0.0) / p.tau_onset)
    top = integrated.max()
    if top <= 0:
        return -np.inf
    value = top
    if p.q > 1.0:
        rel = integrated / top
        value = top * float((weight * rel ** p.q).sum() / (weight * rel ** (p.q - 1.0)).sum())
    out = _level_of(np.log10(value), p.loudness)
    if parts:
        return out, {"level": level, "moment": moment, "integrated": integrated, "weight": weight}
    return out


def matching_gain(a: Track, b: Track, p: Params, tol: float = 0.01) -> float:
    """dB by which sound B is raised to be as loud as sound A."""
    target = event_level(a, p)
    g0, l0 = 0.0, event_level(b, p)
    g1 = target - l0
    for _ in range(40):
        l1 = event_level(b, p, g1)
        if abs(l1 - target) < tol or g1 == g0:
            break
        slope = min(max((l1 - l0) / (g1 - g0), 0.2), 5.0)
        g0, l0, g1 = g1, l1, g1 + (target - l1) / slope
    return float(g1)


def level_of_ears(ears_pa: list[np.ndarray], p: Params | None = None) -> float:
    """Event loudness level of a sound from its ear signals (pressure in Pa at 48 kHz): the two ears' loudness averaged."""
    p = p or FITTED
    levels = [event_level(track(e, p.shelf_db), p) for e in ears_pa]
    if len(levels) == 1 or not all(np.isfinite(levels)):
        return float(levels[0])
    mean = np.mean([10 ** float(_log_sone(np.array(v), p.loudness)) for v in levels])
    return _level_of(np.log10(mean), p.loudness)


FITTED = Params()   # replaced by the fitted values in fitted.py when that file exists
try:  # pragma: no cover
    from .fitted import FITTED_VALUES
    FITTED = replace(Params(), **FITTED_VALUES)
except ImportError:
    pass
