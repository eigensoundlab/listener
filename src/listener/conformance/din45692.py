# SPDX-License-Identifier: Apache-2.0
"""DIN 45692:2009 sharpness test signals (narrow-band and broadband noises).

The signals belong to the standard. Point `--din45692` at a folder holding narrowband_*.wav and broadband_*.wav
(MoSQITo's repository carries a copy with the reference values in validations/sq_metrics/sharpness_din).
Tolerance: 5 % or 0.05 acum, whichever is wider. Two values are given for each signal: MoSQITo's stationary method,
which is what the standard's values are defined for, and the median of listener's per-frame values, which is what
`listener measure` reports per event.
"""
from __future__ import annotations

import contextlib
import glob
import io
import os
import re

import numpy as np
import soundfile as sf

from .. import zwicker


def reference_table(folder: str) -> dict[str, float]:
    """Reference sharpness per file, read from MoSQITo's validation script next to the signals."""
    for cand in (os.path.join(folder, "..", "validation_sharpness_din.py"), os.path.join(folder, "reference.json")):
        if os.path.isfile(cand) and cand.endswith(".py"):
            text = open(cand, encoding="utf-8").read()
            pairs = re.findall(r'"data_file":\s*"input/([^"]+)",(?:\s*"type":\s*"[^"]*",)?\s*"S":\s*([0-9.]+)', text)
            return {name.lower(): float(val) for name, val in pairs}
        if os.path.isfile(cand):
            import json
            return {k.lower(): float(v) for k, v in json.load(open(cand, encoding="utf-8")).items()}
    return {}


def cases(folder: str) -> list[dict]:
    with contextlib.redirect_stdout(io.StringIO()):
        from mosqito.sq_metrics import sharpness_din_st
    ref = reference_table(folder)
    out = []
    files = sorted(glob.glob(os.path.join(folder, "*.wav")) + glob.glob(os.path.join(folder, "*.WAV")),
                   key=lambda p: (os.path.basename(p).split("_")[0], int(re.search(r"_(\d+)", p).group(1))))
    for wav in files:
        name = os.path.basename(wav)
        expected = ref.get(name.lower())
        if expected is None:
            continue
        x, sr = sf.read(wav, dtype="float64", always_2d=True)
        x = x[:, 0]  # these files are already in Pa
        with contextlib.redirect_stdout(io.StringIO()):
            stationary = float(sharpness_din_st(x, sr, weighting="din"))
        curve = zwicker.Zwicker(x).curve(1.0, specific=True)
        s = zwicker.sharpness_din(curve)
        steady = slice(int(0.5 / zwicker.FRAME_S), curve.frames_signal)
        per_frame = float(np.median(s[steady]))
        tol = max(0.05 * expected, 0.05)
        out.append({
            "suite": "din45692", "case": name, "signal": name.split(".")[0].replace("_", " ") + " Hz", "expected": expected,
            "tolerance": [-round(tol, 3), round(tol, 3)], "unit": "acum",
            "measured": round(stationary, 3), "perFrameMedian": round(per_frame, 3),
            "worstDeviation": round(stationary - expected, 3),
            "pass": bool(abs(stationary - expected) <= tol + 1e-9),
            "perFramePass": bool(abs(per_frame - expected) <= tol + 1e-9),
            "source": "DIN 45692:2009 test signals",
        })
    return out
