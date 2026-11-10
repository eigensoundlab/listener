# SPDX-License-Identifier: Apache-2.0
"""ISO 532-1:2017 time-varying loudness (Zwicker) and DIN 45692 sharpness, through MoSQITo 1.2.1.

Nothing of the method is reimplemented here. MoSQITo's own stages are called one by one instead of its
`loudness_zwtv` wrapper for one reason: the filter bank is linear, so a change of playback level or gain is a constant
added to the third-octave levels, and the bank runs once per signal for any number of levels. `tests/test_zwicker.py`
checks that this path returns what `loudness_zwtv` returns.

Domain: ISO 532-1 was validated on tones, noises and the technical sounds of its Annex B. Published tests on impulsive
sounds find it 4 to 12 dB off on single items (Sottek and Moll 2015). On sound effects it is a model, not a listener.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass

import numpy as np

from .audio import MODEL_RATE

FRAME_S = 0.002  # MoSQITo returns N(t) every 2 ms
TAIL_S = 0.5     # silence added after the signal so the loudness decay is inside the curve (ISO signals end the same way)
LAG_S = 0.02     # the curve peaks up to about 6 ms after a short sound has ended: a span is read this much further
N5_PERCENTILE = 95.0


def _stages():
    with contextlib.redirect_stdout(io.StringIO()):
        from mosqito.sq_metrics.loudness.loudness_zwst._calc_slopes import _calc_slopes
        from mosqito.sq_metrics.loudness.loudness_zwst._main_loudness import _main_loudness
        from mosqito.sq_metrics.loudness.loudness_zwtv._nonlinear_decay import _nl_loudness
        from mosqito.sq_metrics.loudness.loudness_zwtv._temporal_weighting import _temporal_weighting
        from mosqito.sq_metrics.loudness.loudness_zwtv._third_octave_levels import _third_octave_levels
    return _third_octave_levels, _main_loudness, _nl_loudness, _calc_slopes, _temporal_weighting


def sone_to_phon(n) -> np.ndarray | float:
    """Loudness level from loudness, ISO 532-1 (above and below 1 sone)."""
    n = np.asarray(n, dtype=float)
    out = np.where(n >= 1.0, 40.0 + 33.22 * np.log10(np.maximum(n, 1e-12)), 40.0 * (np.maximum(n, 0.0) + 0.0005) ** 0.35)
    return float(out) if out.ndim == 0 else out


def phon_to_sone(p: float) -> float:
    return float(2 ** ((p - 40.0) / 10.0)) if p >= 40.0 else float(max((p / 40.0) ** (1 / 0.35) - 0.0005, 0.0))


@dataclass
class Curve:
    n: np.ndarray            # total loudness, sone, every 2 ms
    n_specific: np.ndarray | None  # (240 bark steps, frames) sone/Bark, or None when not asked for
    frames_signal: int       # frames that belong to the signal (the rest is the added tail)

    def span(self, start: float, end: float) -> slice:
        """Frames of a span, read LAG_S past its end: the model's loudness lags the sound."""
        a = max(0, int(round(start / FRAME_S)))
        b = min(len(self.n), max(a + 1, int(round((end + LAG_S) / FRAME_S))))
        return slice(a, b)


class Zwicker:
    """One ear signal at 48 kHz, in full-scale units. Loudness at any calibration without running the filter bank again."""

    def __init__(self, x_fs: np.ndarray, field: str = "free"):
        third, self._main, self._nl, self._slopes, self._weight = _stages()
        self.field = field
        self.frames_signal = int(np.ceil(len(x_fs) / MODEL_RATE / FRAME_S))
        x = np.concatenate([np.asarray(x_fs, dtype=np.float64), np.zeros(int(TAIL_S * MODEL_RATE))])
        with contextlib.redirect_stdout(io.StringIO()):
            # levels for 1.0 = 1 Pa; other calibrations are offsets in dB
            self._spec, _, _ = third(x, MODEL_RATE)

    def curve(self, pa_per_fs: float, gain_db: float = 0.0, specific: bool = False,
              frames: slice | None = None) -> Curve:
        """N(t) at a calibration and gain. `frames` (2 ms frames) limits the work to a part of the signal."""
        offset = 20.0 * np.log10(pa_per_fs) + gain_db
        spec = self._spec
        lo = 0
        if frames is not None:  # the bank's levels are every 0.5 ms: four per output frame
            lo = (frames.start or 0) * 4
            spec = spec[:, lo:(frames.stop * 4 if frames.stop is not None else None)]
        with contextlib.redirect_stdout(io.StringIO()):
            core = self._nl(self._main(spec + offset, self.field))
            total, spec_loud = self._slopes(core)
            n = self._weight(total)[::4]
        return Curve(np.asarray(n), np.asarray(spec_loud[:, ::4]) if specific else None,
                     self.frames_signal if frames is None else len(n))

    def gain_for_level(self, pa_per_fs: float, target_phon: float, statistic: str = "max",
                       tol: float = 0.05, max_iter: int = 7, around: tuple[float, float] | None = (1.0, 0.3)) -> dict:
        """The gain in dB that brings this signal's loudness level (maximum or N5) to target_phon at this calibration.

        Loudness is not linear in level: at low frequencies one dB of gain is worth more than one phon. The gain is
        found by iteration (secant, first step one phon per dB). For the maximum, the iterations run on the part of the
        signal around the loudest moment (`around`: seconds before and after it); None runs them on all of it.
        """
        n0 = self.curve(pa_per_fs).n
        frames = None
        if statistic == "max" and around is not None:
            peak = int(np.argmax(n0))
            frames = slice(max(0, peak - int(around[0] / FRAME_S)), min(len(n0), peak + int(around[1] / FRAME_S)))

        def stat(n: np.ndarray) -> float:
            if statistic == "max":
                return float(sone_to_phon(n.max()))
            return float(sone_to_phon(np.percentile(n[: self.frames_signal + int(LAG_S / FRAME_S)], N5_PERCENTILE)))

        def level(gain: float) -> float:
            return stat(self.curve(pa_per_fs, gain, frames=frames).n)

        start = stat(n0)
        g0, l0 = 0.0, (level(0.0) if frames is not None else start)
        g1, l1, evals = target_phon - l0, l0, 1
        for _ in range(max_iter):
            l1 = level(g1)
            evals += 1
            if abs(l1 - target_phon) < tol or g1 == g0:
                break
            slope = min(max((l1 - l0) / (g1 - g0), 0.2), 5.0)
            g0, l0, g1 = g1, l1, g1 + (target_phon - l1) / slope
        return {"gainDb": float(g1), "levelPhon": float(l1), "startPhon": start, "evaluations": evals,
                "converged": bool(abs(l1 - target_phon) < 4 * tol)}


def sharpness_din(curve: Curve) -> np.ndarray:
    """DIN 45692 sharpness (acum) for every frame of a curve computed with specific=True (MoSQITo)."""
    with contextlib.redirect_stdout(io.StringIO()):
        from mosqito.sq_metrics.sharpness.sharpness_din.sharpness_din_from_loudness import sharpness_din_from_loudness
        with np.errstate(divide="ignore", invalid="ignore"):
            s = sharpness_din_from_loudness(curve.n, curve.n_specific, weighting="din")
    return np.nan_to_num(np.asarray(s, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)


def combine_ears(curves: list[tuple[Curve, int]]) -> Curve:
    """ISO 532-1 gives one value per ear signal. A file's value is the mean of the two ears' loudness."""
    if len(curves) == 1:
        return curves[0][0]
    n = sum(c.n * w for c, w in curves) / sum(w for _, w in curves)
    spec = None
    if all(c.n_specific is not None for c, _ in curves):
        spec = sum(c.n_specific * w for c, w in curves) / sum(w for _, w in curves)
    return Curve(n, spec, curves[0][0].frames_signal)


def span_stats(curve: Curve, start: float, end: float, sharp: np.ndarray | None = None) -> dict:
    """Maximum and N5 of the loudness in a span, as sone and phon; sharpness where the span is loud enough to have one."""
    sl = curve.span(start, end)
    n = curve.n[sl]
    out = {
        "nMax": round(float(n.max()), 4),
        "n5": round(float(np.percentile(n, N5_PERCENTILE)), 4),
        "levelMax": round(float(sone_to_phon(n.max())), 2),
        "level5": round(float(sone_to_phon(np.percentile(n, N5_PERCENTILE))), 2),
    }
    if sharp is not None:
        s = sharp[sl]
        loud = n >= max(0.25 * n.max(), 0.05)  # sharpness is a ratio: undefined in quiet frames
        if loud.any():
            out["sharpness"] = {
                "atNMax": round(float(s[int(np.argmax(n))]), 3),
                "median": round(float(np.median(s[loud])), 3),
                "p95": round(float(np.percentile(s[loud], 95)), 3),
                "gate": "frames with N >= 0.25 Nmax of the span",
            }
    return out
