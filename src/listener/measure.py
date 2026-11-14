# SPDX-License-Identifier: Apache-2.0
"""`listener measure`: every measure per file and per Playhead event, at stated playback levels.

Output: JSON, "format": "listener-measures", version 1. See docs/FORMAT.md.
"""
from __future__ import annotations

import datetime
import os
from importlib.metadata import PackageNotFoundError, version

import numpy as np

from . import __version__, bs1770, ecma, spans as spans_mod, zwicker
from .model import literature
from .audio import ear_signals, load, to_model_rate
from .calibration import Level
from .domains import DOMAINS, NOTES

FORMAT = "listener-measures"
FORMAT_VERSION = 1
AUDIO_EXTENSIONS = (".wav", ".flac", ".ogg", ".aif", ".aiff", ".mp3", ".m4a", ".opus")


def _pkg(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "?"


def implementations(ecma_python: str | None) -> dict:
    return {
        "bs1770": f"pyloudnorm {_pkg('pyloudnorm')} (K-weighting filter, loudness range); listener {__version__} (gating on complete blocks, 0.4 s and 3 s windows, true peak, spans)",
        "iso532_1": f"MoSQITo {_pkg('mosqito')} loudness_zwtv stages (ISO 532-1:2017 time-varying, free field)",
        "din45692": f"MoSQITo {_pkg('mosqito')} sharpness_din_from_loudness on the ISO 532-1 specific loudness",
        "ecma418_2": "sottek-hearing-model, as a separate process" if ecma_python else None,
        "iso532_3": None,
        "literatureL0": f"listener {__version__} model/literature.py, parameters {literature.FITTED.beta:g}, {literature.FITTED.t_half:g} s, {literature.FITTED.shelf_db:g} dB",
    }


def list_audio(paths: list[str]) -> list[str]:
    out: list[str] = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in sorted(os.walk(p, followlinks=True)):
                out += [os.path.join(root, f) for f in sorted(files) if f.lower().endswith(AUDIO_EXTENSIONS)]
        else:
            out.append(p)
    return out


def _parity(playhead_levels: dict | None, span_values: dict) -> dict | None:
    """listener minus Playhead for the measures both compute on the same span (dB)."""
    if not playhead_levels:
        return None
    out = {}
    for scope, span_id in (("file", "file"), ("active", "active"), ("event", "loudest-event")):
        theirs, ours = playhead_levels.get(scope), span_values.get(span_id)
        if not theirs or not ours:
            continue
        for key in ("rms", "integrated", "momentaryMax", "shortTermMax"):
            if theirs.get(key) is not None and ours.get(key) is not None:
                out[f"{key}@{scope}"] = round(ours[key] - theirs[key], 2)
    return out or None


def measure_file(path: str, levels: list[Level], docs_dir: str | None = None, ecma_python: str | None = None,
                 curves: bool = False, roughness: bool = True, base_dir: str | None = None) -> dict:
    x, sr, meta = load(path)
    rel = os.path.relpath(path, base_dir).replace(os.sep, "/") if base_dir else os.path.basename(path)
    entry: dict = {"path": rel, "duration": round(meta["duration"], 4), "sampleRate": sr,
                   "channels": meta["channels"], "notes": []}
    doc_path = spans_mod.find_document(path, docs_dir)
    doc = spans_mod.read_document(doc_path) if doc_path else None
    span_list, ph = spans_mod.spans_for(meta["duration"], doc)
    if doc is None:
        entry["notes"].append("no-playhead-document")

    # --- level-free measures (BS.1770 family)
    ky = bs1770.k_weight(x, sr)
    entry["peak"] = round(float(20 * np.log10(max(np.abs(x).max(), 1e-12))), 2)
    entry["truePeak"] = round(bs1770.true_peak_db(x), 2)
    lra = bs1770.loudness_range(x, sr)
    if lra is not None:
        entry["loudnessRange"] = round(lra, 2)
    out_spans = []
    for sp in span_list:
        values, notes = bs1770.measure_span(x, ky, sr, sp.start, sp.end)
        out_spans.append({"id": sp.id, "kind": sp.kind, "start": round(sp.start, 4), "end": round(sp.end, 4),
                          **({k: v for k, v in sp.extra.items() if v is not None}),
                          "bs1770": values, "byLevel": {}, "notes": notes})

    # --- hearing models: ear signals at 48 kHz
    x48 = to_model_rate(x, sr)
    if x48.shape[1] > 2:
        entry["notes"].append("more-than-two-channels")
    ears = ear_signals(x48[:, :2])
    entry["ears"] = "both ears hear the same signal" if len(ears) == 1 else "left and right differ"
    models = [(zwicker.Zwicker(sig), weight) for sig, weight in ears]
    curve_out: dict = {}
    for lv in levels:
        per_ear = [(m.curve(lv.pa_per_fs, specific=True), w) for m, w in models]
        curve = zwicker.combine_ears(per_ear)
        sharp = zwicker.sharpness_din(curve)
        for sp, rec in zip(span_list, out_spans):
            stats = zwicker.span_stats(curve, sp.start, sp.end, sharp)
            sharp_stats = stats.pop("sharpness", None)
            rec["byLevel"][lv.id] = {"iso532_1": stats}
            a48, b48 = int(round(sp.start * 48000)), max(int(round(sp.end * 48000)), int(round(sp.start * 48000)) + 48)
            lit = literature.level_of_ears([sig[a48:b48] * lv.pa_per_fs for sig, _ in ears])
            if np.isfinite(lit):
                rec["byLevel"][lv.id]["literatureL0"] = {"level": round(lit, 2)}
            if sharp_stats:
                rec["byLevel"][lv.id]["din45692"] = sharp_stats
        if curves:
            keep = curve.n[: curve.frames_signal + int(0.2 / zwicker.FRAME_S)]
            curve_out[lv.id] = {"iso532_1": {"rate": 100.0, "unit": "sone",
                                             "n": [round(float(v), 3) for v in keep[::5]]}}
        if ecma_python:
            try:
                res = ecma.run([sig for sig, _ in ears], lv.pa_per_fs, ecma_python, roughness=roughness)
                for sp, rec in zip(span_list, out_spans):
                    stats, notes = ecma.span_stats(res, sp.start, sp.end, sp.kind == "file")
                    rec["byLevel"][lv.id]["ecma418_2"] = stats
                    rec["notes"] = sorted(set(rec["notes"]) | set(notes))
                if curves:
                    step = max(1, int(round(0.01 / float(np.median(np.diff(res["time"]))))))
                    keep = res["time"] >= 0
                    curve_out[lv.id]["ecma418_2"] = {"rate": round(1.0 / float(np.median(np.diff(res["time"]))) / step, 3),
                                                     "unit": "sone_HMS",
                                                     "n": [round(float(v), 3) for v in res["loudness"][keep][::step]]}
            except Exception as exc:  # the oracle is optional: say why it is missing
                entry.setdefault("errors", []).append(f"ecma418_2@{lv.id}: {str(exc)[:300]}")
    entry["spans"] = out_spans
    if curves:
        entry["curves"] = curve_out
    if ph:
        by_id = {s["id"]: s["bs1770"] for s in out_spans}
        loudest = next((s for s in out_spans if s.get("loudest")), None)
        if loudest:
            by_id["loudest-event"] = loudest["bs1770"]
        levels_block = ph.pop("levels", None)
        ph["document"] = os.path.basename(doc_path)
        # Playhead's @event span ends where the event has decayed 35 dB, ours at the event's end: compare file and active
        parity = _parity({k: v for k, v in (levels_block or {}).items() if k in ("file", "active")}, by_id)
        if parity:
            ph["listenerMinusPlayhead"] = parity
        entry["playhead"] = ph
    return entry


def measure(paths: list[str], levels: list[Level], docs_dir: str | None = None, ecma_python: str | None = None,
            curves: bool = False, roughness: bool = True, jobs: int = 1, progress=None) -> dict:
    files = list_audio(paths)
    base = os.path.commonpath([os.path.abspath(f) for f in files]) if len(files) > 1 else None
    if base and os.path.isfile(base):
        base = os.path.dirname(base)
    args = [(f, levels, docs_dir, ecma_python, curves, roughness, base) for f in files]
    if jobs > 1 and len(files) > 1:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(jobs) as pool:
            results = []
            for i, r in enumerate(pool.imap(_star, args)):
                results.append(r)
                if progress:
                    progress(i + 1, len(files), files[i])
    else:
        results = []
        for i, a in enumerate(args):
            results.append(_star(a))
            if progress:
                progress(i + 1, len(files), files[i])
    return {
        "format": FORMAT,
        "version": FORMAT_VERSION,
        "generator": {"name": "listener", "version": __version__},
        "created": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "calibration": {
            "convention": "The digital signal is what reaches each ear; a mono file is heard in both ears. Levels state what a 1 kHz reference tone plays at.",
            "levels": [lv.describe() for lv in levels],
        },
        "implementations": implementations(ecma_python),
        "domains": DOMAINS,
        "notes": NOTES,
        "units": {"bs1770": "LUFS (peak, rms: dBFS)", "iso532_1": "nMax, n5: sone; levelMax, level5: phon",
                  "din45692": "acum", "ecma418_2": "loudness: sone_HMS; tonality: tu_HMS; roughness: asper_HMS",
                  "literatureL0": "level: dB, the level of a steady 1 kHz tone predicted to be as loud as the span"},
        "files": results,
    }


def _star(a):
    try:
        return measure_file(*a)
    except Exception as exc:
        return {"path": os.path.basename(a[0]), "error": f"{type(exc).__name__}: {str(exc)[:300]}"}
