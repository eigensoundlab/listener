# SPDX-License-Identifier: Apache-2.0
"""ECMA-418-2:2025 (Sottek hearing model) loudness, tonality and roughness, from a tool run as a separate process.

The verified open implementations are under copyleft licences, so nothing of them is imported here: this module writes
the ear signals to a temporary file, starts `external/ecma418_2_worker.py` with the Python interpreter named by
LISTENER_ECMA_PYTHON, and reads its JSON.

Single values: the standard's own (power average of loudness, 90th percentile of roughness) skip about the first
300 ms and average what follows, so on a one-shot they depend on the silence around it. Per span this module gives
the maximum and the 90th percentile of the time-dependent values instead, and labels the standard's value as such.

Domain: verified against one commercial tool on two field recordings (Lotinga et al. 2025); the standard has no test
signals. Short and impulsive sounds have not been verified by anyone.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile

import numpy as np

from .audio import MODEL_RATE

LEAD_S = 0.3   # silence before the sound: the model's first blocks start inside it
TAIL_S = 0.5
WORKER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                      "external", "ecma418_2_worker.py")


def interpreter(explicit: str | None = None) -> str | None:
    py = explicit or os.environ.get("LISTENER_ECMA_PYTHON")
    return py if py and os.path.exists(py) else None


def worker_path() -> str | None:
    cand = os.environ.get("LISTENER_ECMA_WORKER") or WORKER
    return cand if os.path.isfile(cand) else None


def run(ears_fs: list[np.ndarray], pa_per_fs: float, python: str, roughness: bool = True, timeout: float = 3600) -> dict:
    """Time-dependent ECMA-418-2 values of the ear signals (full-scale units at 48 kHz) at a calibration."""
    worker = worker_path()
    if worker is None:
        raise FileNotFoundError("external/ecma418_2_worker.py not found (set LISTENER_ECMA_WORKER)")
    lead, tail = np.zeros(int(LEAD_S * MODEL_RATE)), np.zeros(int(TAIL_S * MODEL_RATE))
    p = np.stack([np.concatenate([lead, e * pa_per_fs, tail]) for e in ears_fs], axis=1)
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = os.path.join(tmp, "p.npz"), os.path.join(tmp, "out.json")
        np.savez(src, p=p)
        cmd = [python, "-I", worker, src, dst] + ([] if roughness else ["--no-roughness"])
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if res.returncode != 0 or not os.path.isfile(dst):
            raise RuntimeError("ECMA-418-2 worker failed: " + (res.stderr or res.stdout)[-400:])
        with open(dst, encoding="utf-8") as fh:
            raw = json.load(fh)
    ears = raw["ears"]

    def quad(key):  # ECMA-418-2 combines the two ears by their quadratic mean
        arr = np.array([e[key] for e in ears if key in e], dtype=float)
        return np.sqrt((arr ** 2).mean(axis=0)) if arr.size else None

    out = {
        "implementation": f'{raw.get("implementation")} {raw.get("version", "")}'.strip(),
        "time": np.asarray(ears[0]["time"]) - LEAD_S,
        "loudness": quad("loudness"),
        "tonality": np.max(np.array([e["tonality"] for e in ears], dtype=float), axis=0),
        "standardLoudness": float(np.sqrt(np.mean([e["loudnessPowAvg"] ** 2 for e in ears]))),
        "standardTonality": float(max(e["tonalityAvg"] for e in ears)),
    }
    if all("roughness" in e for e in ears):
        out["roughnessTime"] = np.asarray(ears[0]["roughnessTime"]) - LEAD_S
        out["roughness"] = quad("roughness")
        out["standardRoughness"] = float(np.sqrt(np.mean([e["roughness90"] ** 2 for e in ears])))
    else:
        out["roughnessError"] = next((e.get("roughnessError") for e in ears if "roughnessError" in e), "not computed")
    return out


def span_stats(res: dict, start: float, end: float, whole_file: bool) -> tuple[dict, list[str]]:
    notes: list[str] = []
    t = res["time"]
    # the model's loudness lags the sound by its block lengths: let the span run on a little
    sel = (t >= start) & (t <= end + 0.1)
    if not sel.any():
        sel = np.zeros_like(t, dtype=bool)
        sel[int(np.argmin(np.abs(t - start)))] = True
    n = res["loudness"][sel]
    out = {
        "loudnessMax": round(float(n.max()), 4),
        "loudness90": round(float(np.percentile(n, 90)), 4),
        "tonalityMax": round(float(res["tonality"][sel].max()), 4),
    }
    if "roughness" in res:
        rt = res["roughnessTime"]
        rsel = (rt >= start) & (rt <= end + 0.1)
        if rsel.any():
            out["roughnessMax"] = round(float(res["roughness"][rsel].max()), 4)
            out["roughness90"] = round(float(np.percentile(res["roughness"][rsel], 90)), 4)
        if end - start < 0.5:
            notes.append("roughness-short-span")
    if whole_file:
        out["standardSingleValues"] = {
            "loudnessPowAvg": round(res["standardLoudness"], 4),
            "tonalityAvg": round(res["standardTonality"], 4),
            **({"roughness90": round(res["standardRoughness"], 4)} if "standardRoughness" in res else {}),
            "note": "ECMA-418-2's own single values: they skip about the first 300 ms and depend on the silence around a one-shot",
        }
    return out, notes
