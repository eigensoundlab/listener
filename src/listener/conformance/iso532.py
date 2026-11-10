# SPDX-License-Identifier: Apache-2.0
"""ISO 532-1:2017 Annex B.4 (synthetic) and B.5 (technical) time-varying test signals.

The signals and reference spreadsheets belong to the standard and are not part of this repository. Point `--iso532-1`
at a folder that holds "Annex B.4" and "Annex B.5" (bought with the standard; MoSQITo's repository carries a copy under
validations/sq_metrics/loudness_zwtv/input/ISO_532-1).

Pass rule, as in MoSQITo's validation: N(t) within the 5 % band (5 % or 0.1 sone, whichever is wider) for at least
99 % of the time, after the 2 ms time shift the standard allows. The 16-bit files need a factor of 2*sqrt(2).
"""
from __future__ import annotations

import glob
import os
import re
import warnings

import numpy as np
import soundfile as sf

from .. import zwicker

CAL_16_BIT = 2.0 * np.sqrt(2.0)


def _reference(xlsx: str, sheet: str):
    import openpyxl
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wb = openpyxl.load_workbook(xlsx, data_only=True, read_only=True)
        ws = wb[sheet]
        rows = list(ws.iter_rows(min_row=1, max_col=2, values_only=True))
    n_max, n5 = float(rows[4][1]), float(rows[5][1])
    field = "diffuse" if "diffuse" in str(rows[4][0]).lower() else "free"
    curve = np.array([float(r[1]) for r in rows[10:] if r[0] is not None and r[1] is not None])
    return n_max, n5, curve, field


def _within(n: np.ndarray, ref: np.ndarray, rel: float, absolute: float) -> np.ndarray:
    lo = np.minimum(ref * (1 - rel), ref - absolute)
    hi = np.maximum(ref * (1 + rel), ref + absolute)
    return (n >= lo) & (n <= hi)


def check_signal(wav: str, xlsx: str, sheet: str) -> dict:
    info = sf.info(wav)
    x, sr = sf.read(wav, dtype="float64", always_2d=True)
    x = x[:, 0] * (CAL_16_BIT if info.subtype == "PCM_16" else 1.0)  # now in Pa
    ref_max, ref_n5, ref, field = _reference(xlsx, sheet)
    model = zwicker.Zwicker(x, field=field)
    n = model.curve(1.0).n  # 1.0 = 1 Pa
    m = min(len(n), len(ref))
    best = None
    for shift in (0, 1, -1):  # the 2 ms the standard allows
        a = n[max(0, shift):m + min(0, shift)] if shift >= 0 else n[:m + shift]
        b = ref[:m - shift] if shift >= 0 else ref[-shift:m]
        k = min(len(a), len(b))
        ok5 = _within(a[:k], b[:k], 0.05, 0.1)
        ok10 = _within(a[:k], b[:k], 0.10, 0.2)
        score = (ok5.mean(), ok10.mean())
        if best is None or score > best[0]:
            best = (score, shift)
    (in5, in10), shift = best
    # N5 depends on how much silence is counted. The standard's values follow no single rule across its signals,
    # so the value is given under each rule and the closest one is named; it is not part of the pass rule.
    lead, tail, end = int(0.1 / zwicker.FRAME_S), int(0.5 / zwicker.FRAME_S), len(ref)
    n5_rules = {
        "whole file": float(np.percentile(n[:end], 95)),
        "without the first 100 ms": float(np.percentile(n[lead:end], 95)),
        "without the first 100 ms and the last 500 ms": float(np.percentile(n[lead:end - tail], 95)),
    }
    n5_rule = min(n5_rules, key=lambda k: abs(n5_rules[k] - ref_n5))
    return {
        "suite": "iso532-1", "case": int(re.search(r"(\d+)", sheet).group(1)),
        "signal": re.search(r"\((.*)\)\.wav$", os.path.basename(wav)).group(1),
        "expected": {"nMax": ref_max, "n5": ref_n5}, "unit": "sone",
        "field": field,
        "measured": {"nMax": round(float(n[:m].max()), 4), "n5": round(n5_rules[n5_rule], 4)},
        "n5ByRule": {k: round(v, 4) for k, v in n5_rules.items()}, "n5ClosestRule": n5_rule,
        "n5Reproduced": bool(abs(n5_rules[n5_rule] - ref_n5) <= max(0.05 * ref_n5, 0.1)),
        "within5Percent": round(float(in5), 5), "within10Percent": round(float(in10), 5), "shiftFrames": shift,
        "tolerance": "N(t) within 5 % or 0.1 sone for at least 99 % of the time, and Nmax within 5 %",
        "pass": bool(in5 >= 0.99 and abs(float(n[:m].max()) - ref_max) <= max(0.05 * ref_max, 0.1)),
        "source": "ISO 532-1:2017 Annex B, reference spreadsheet",
    }


def cases(folder: str) -> list[dict]:
    out = []
    for annex in ("Annex B.4", "Annex B.5"):
        d = os.path.join(folder, annex)
        xl = glob.glob(os.path.join(d, "*.xlsx"))
        if not xl:
            continue
        for wav in sorted(glob.glob(os.path.join(d, "*.wav")), key=lambda p: int(re.search(r"signal (\d+)", p).group(1))):
            num = re.search(r"signal (\d+)", wav).group(1)
            try:
                out.append(check_signal(wav, xl[0], f"Test signal {num}"))
            except Exception as exc:
                out.append({"suite": "iso532-1", "case": int(num), "pass": False, "error": str(exc)[:200]})
    return out
