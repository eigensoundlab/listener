# SPDX-License-Identifier: Apache-2.0
"""The reference sounds that define each unit, built from their definitions. No purchased files needed.

- 1 sone (ISO 532-1): a 1 kHz tone at 40 dB SPL, free field.
- 1 acum (DIN 45692): noise one critical band wide (920 to 1080 Hz) centred on 1 kHz, at 60 dB SPL.
- 1 sone_HMS (ECMA-418-2): a 1 kHz tone at 40 dB SPL.
- 1 asper_HMS (ECMA-418-2): a 1 kHz tone at 60 dB SPL, fully amplitude-modulated at 70 Hz.
- 1 vacil (ECMA-418-2, 4th edition): the same tone modulated at 4 Hz. No open implementation of Clause 9 was found.

ECMA-418-2 gives no tolerances; 5 % is used here and said so.
"""
from __future__ import annotations

import numpy as np

from .. import ecma, zwicker
from ..calibration import P0

SR = 48000


def tone(spl: float, seconds: float = 2.0, freq: float = 1000.0) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    x = np.sqrt(2) * P0 * 10 ** (spl / 20) * np.sin(2 * np.pi * freq * t)
    ramp = int(0.02 * SR)
    x[:ramp] *= np.linspace(0, 1, ramp)
    x[-ramp:] *= np.linspace(1, 0, ramp)
    return x


def narrow_band_noise(spl: float, lo: float = 920.0, hi: float = 1080.0, seconds: float = 4.0, seed: int = 1) -> np.ndarray:
    n = int(seconds * SR)
    spec = np.fft.rfft(np.random.default_rng(seed).standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec[(f < lo) | (f > hi)] = 0
    x = np.fft.irfft(spec, n)
    return x / np.sqrt((x ** 2).mean()) * P0 * 10 ** (spl / 20)


def am_tone(spl: float, mod_hz: float, seconds: float = 3.0) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    x = (1 + np.sin(2 * np.pi * mod_hz * t)) * np.sin(2 * np.pi * 1000 * t)
    # the level is that of the unmodulated tone
    return x * np.sqrt(2) * P0 * 10 ** (spl / 20)


def _case(case, text, expected, measured, unit, tol_text, tol):
    return {"suite": "reference-tones", "case": case, "signal": text, "expected": expected, "unit": unit,
            "measured": round(float(measured), 4), "worstDeviation": round(float(measured - expected), 4),
            "tolerance": [-tol, tol], "toleranceNote": tol_text, "pass": bool(abs(measured - expected) <= tol),
            "source": "definition of the unit"}


def cases(ecma_python: str | None) -> list[dict]:
    out = []
    steady = slice(int(0.5 / zwicker.FRAME_S), int(1.5 / zwicker.FRAME_S))
    n = zwicker.Zwicker(tone(40.0)).curve(1.0).n[steady]
    out.append(_case("1 sone", "1 kHz tone, 40 dB SPL (ISO 532-1, free field)", 1.0, np.median(n), "sone",
                     "ISO 532-1: 5 % or 0.1 sone", 0.1))
    c = zwicker.Zwicker(narrow_band_noise(60.0)).curve(1.0, specific=True)
    s = zwicker.sharpness_din(c)[int(0.5 / zwicker.FRAME_S): c.frames_signal]
    out.append(_case("1 acum", "noise 920-1080 Hz, 60 dB SPL (DIN 45692)", 1.0, np.median(s), "acum",
                     "DIN 45692: 5 % or 0.05 acum", 0.05))
    if not ecma_python:
        for name in ("1 sone_HMS", "1 asper_HMS"):
            out.append({"suite": "reference-tones", "case": name, "pass": None,
                        "skipped": "needs the ECMA-418-2 tool: --ecma with LISTENER_ECMA_PYTHON"})
    else:
        r = ecma.run([tone(40.0, 3.0)], 1.0, ecma_python, roughness=False)
        sel = (r["time"] > 1.0) & (r["time"] < 2.5)
        out.append(_case("1 sone_HMS", "1 kHz tone, 40 dB SPL (ECMA-418-2)", 1.0, np.median(r["loudness"][sel]),
                         "sone_HMS", "none in the standard; 5 % used", 0.05))
        r = ecma.run([am_tone(60.0, 70.0)], 1.0, ecma_python, roughness=True)
        sel = (r["roughnessTime"] > 1.0) & (r["roughnessTime"] < 2.5)
        out.append(_case("1 asper_HMS", "1 kHz tone, 60 dB SPL, 100 % AM at 70 Hz (ECMA-418-2)", 1.0,
                         np.median(r["roughness"][sel]), "asper_HMS", "none in the standard; 5 % used", 0.05))
    out.append({"suite": "reference-tones", "case": "1 vacil", "pass": None,
                "skipped": "ECMA-418-2 Clause 9 (fluctuation strength, 2025): no open implementation found"})
    return out
