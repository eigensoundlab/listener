# SPDX-License-Identifier: Apache-2.0
"""`listener disagree`: where the measures part on a corpus, in dB of gain, to choose listening-test stimuli.

Every measure is turned into the same thing: the gain it would give each file to make the corpus equally loud. For
peak, RMS and the BS.1770 measures that is a subtraction. For ISO 532-1 it is not: loudness in sone is not linear in
level, and at low frequencies one dB of gain is worth more than one phon, so the gain is solved for (see
`Zwicker.gain_for_level`) at each stated playback level. Differences between two measures' gains, with the corpus
median removed, are then in the unit a listener's correction is in.

Two conventions are applied before comparing and are written into the output:

- Ears. BS.1770 sums the channels' power and counts a mono file once, so the same sound reads 3.01 dB lower as a mono
  file than as a two-channel file. Heard on headphones both reach both ears alike. Here a mono file is taken as heard
  in both ears: its BS.1770 values get +3.01 dB ("asHeard"). The meter's own value stays in "asFile".
- Operating point. Each file is first brought to the calibration's reference loudness by its Max M, so the hearing
  model runs at the level the file would be played at, not at the level it happens to be stored at.

A model stands in for nothing here. The report shows where the choice of measure matters; only listeners say which
measure is right.
"""
from __future__ import annotations

import datetime
import os

import numpy as np

from . import __version__, bs1770, spans as spans_mod, zwicker
from .audio import ear_signals, load, to_model_rate
from .calibration import Level
from .measure import implementations, list_audio

MONO_AS_HEARD_DB = 10 * np.log10(2.0)
LINEAR = ("peak", "rms", "integrated", "momentaryMax", "shortTermMax", "momentaryMax@event")
DURATION_BINS = ((0.05, "under 50 ms"), (0.4, "50 to 400 ms"), (2.0, "0.4 to 2 s"), (1e9, "over 2 s"))
LOW_FREQUENCY_HZ = 150.0
LOW_FREQUENCY_SHARE = 0.4
LONG_TAIL_S = 1.0


def _low_share(x: np.ndarray, sr: int) -> float:
    mono = x.mean(axis=1)
    spec = np.abs(np.fft.rfft(mono)) ** 2
    f = np.fft.rfftfreq(len(mono), 1 / sr)
    total = spec[f >= 20].sum()
    return float(spec[(f >= 20) & (f < LOW_FREQUENCY_HZ)].sum() / total) if total > 0 else 0.0


def _stage_a(args):
    """Per file: the level-free measures, descriptors, and the ISO 532-1 level after Max M normalisation."""
    path, levels, docs_dir = args
    x, sr, meta = load(path)
    ky = bs1770.k_weight(x, sr)
    doc_path = spans_mod.find_document(path, docs_dir)
    doc = spans_mod.read_document(doc_path) if doc_path else None
    span_list, _ = spans_mod.spans_for(meta["duration"], doc)
    values, _ = bs1770.measure_span(x, ky, sr, 0.0, meta["duration"])
    loudest = next((s for s in span_list if s.extra.get("loudest")), None)
    ev = loudest or span_list[0]
    ev_end = ev.extra.get("decayEnd", ev.end) if loudest else ev.end
    ev_values, _ = bs1770.measure_span(x, ky, sr, ev.start, max(ev_end, ev.start + 1e-3))
    as_heard = MONO_AS_HEARD_DB if meta["channels"] == 1 else 0.0
    as_file = {"peak": values["peak"], "rms": values["rms"], "integrated": values["integrated"],
               "momentaryMax": values["momentaryMax"], "shortTermMax": values["shortTermMax"],
               "momentaryMax@event": ev_values["momentaryMax"]}
    heard = {k: (v + as_heard if k not in ("peak", "rms") else v) for k, v in as_file.items()}
    ears = ear_signals(to_model_rate(x, sr)[:, :2])
    models = [(zwicker.Zwicker(sig), w) for sig, w in ears]
    iso = {}
    tail = None
    for lv in levels:
        pre = lv.ref_lufs - heard["momentaryMax"]
        curve = zwicker.combine_ears([(m.curve(lv.pa_per_fs, pre), w) for m, w in models])
        n = curve.n[: curve.frames_signal + int(0.2 / zwicker.FRAME_S)]
        iso[lv.id] = {"preGain": pre, "levelMax": float(zwicker.sone_to_phon(n.max())),
                      "level5": float(zwicker.sone_to_phon(np.percentile(curve.n[: curve.frames_signal], 95)))}
        if tail is None:
            peak = int(np.argmax(n))
            above = np.nonzero(n >= 0.25 * n.max())[0]
            tail = float((above[-1] - peak) * zwicker.FRAME_S)
    return {
        "path": path, "name": os.path.basename(path), "duration": meta["duration"], "channels": meta["channels"],
        "class": (loudest.extra.get("class") if loudest else None), "eventDuration": float(ev_end - ev.start),
        "events": sum(1 for s in span_list if s.kind == "event"), "hasDocument": doc is not None,
        "lowShare": _low_share(x, sr), "tail": tail, "asFile": as_file, "asHeard": heard, "iso": iso,
    }


def _stage_b(args):
    """Per file: the gain that brings its ISO 532-1 maximum to the corpus target, at each level."""
    path, levels, pre_gains, targets = args
    x, sr, _ = load(path)
    ears = ear_signals(to_model_rate(x, sr)[:, :2])
    out = {}
    if len(ears) == 1:
        model = zwicker.Zwicker(ears[0][0])
        for lv in levels:
            pa = lv.pa_per_fs * 10 ** (pre_gains[lv.id] / 20)
            out[lv.id] = model.gain_for_level(pa, targets[lv.id])
    else:  # the file's loudness is the mean of two ears: solve on that mean
        models = [zwicker.Zwicker(sig) for sig, _ in ears]
        for lv in levels:
            pa = lv.pa_per_fs * 10 ** (pre_gains[lv.id] / 20)
            base = np.mean([m.curve(pa).n for m in models], axis=0)
            peak = int(np.argmax(base))
            frames = slice(max(0, peak - int(1.0 / zwicker.FRAME_S)), min(len(base), peak + int(0.3 / zwicker.FRAME_S)))

            def level(g):
                n = np.mean([m.curve(pa, g, frames=frames).n for m in models], axis=0)
                return float(zwicker.sone_to_phon(n.max()))

            target = targets[lv.id]
            g0, l0 = 0.0, level(0.0)
            g1, l1, evals = target - l0, l0, 1
            for _ in range(7):
                l1 = level(g1)
                evals += 1
                if abs(l1 - target) < 0.05 or g1 == g0:
                    break
                slope = min(max((l1 - l0) / (g1 - g0), 0.2), 5.0)
                g0, l0, g1 = g1, l1, g1 + (target - l1) / slope
            out[lv.id] = {"gainDb": float(g1), "levelPhon": float(l1), "evaluations": evals,
                          "converged": bool(abs(l1 - target) < 0.2)}
    return out


def _centre(v: np.ndarray) -> np.ndarray:
    return v - np.median(v)


def _strata(row: dict) -> dict:
    dur = next(label for limit, label in DURATION_BINS if row["eventDuration"] < limit)
    return {"duration": dur, "lowFrequency": bool(row["lowShare"] >= LOW_FREQUENCY_SHARE),
            "longTail": bool(row["tail"] is not None and row["tail"] >= LONG_TAIL_S), "class": row["class"]}


def run(paths: list[str], levels: list[Level], docs_dir: str | None = None, jobs: int = 1, pick: int = 0,
        progress=None) -> dict:
    files = list_audio(paths)

    def pool_map(fn, args):
        if jobs > 1 and len(args) > 1:
            import multiprocessing as mp
            with mp.get_context("spawn").Pool(jobs) as pool:
                res = []
                for i, r in enumerate(pool.imap(fn, args)):
                    res.append(r)
                    if progress:
                        progress(i + 1, len(args), args[i][0])
                return res
        res = []
        for i, a in enumerate(args):
            res.append(fn(a))
            if progress:
                progress(i + 1, len(args), a[0])
        return res

    rows = pool_map(_stage_a, [(f, levels, docs_dir) for f in files])
    targets = {lv.id: float(np.median([r["iso"][lv.id]["levelMax"] for r in rows])) for lv in levels}
    solved = pool_map(_stage_b, [(r["path"], levels, {lv.id: r["iso"][lv.id]["preGain"] for lv in levels}, targets)
                                 for r in rows])

    # gains: what each measure would give each file (dB), corpus median removed
    gains: dict[str, np.ndarray] = {}
    for key in LINEAR:
        gains[key] = _centre(-np.array([r["asHeard"][key] for r in rows]))
    for lv in levels:
        total = np.array([r["iso"][lv.id]["preGain"] + s[lv.id]["gainDb"] for r, s in zip(rows, solved)])
        gains[f"iso532_1.max@{lv.id}"] = _centre(total)
    names = list(gains)
    matrix = np.stack([gains[k] for k in names], axis=1)

    out_files = []
    for i, (r, s) in enumerate(zip(rows, solved)):
        g = {k: round(float(matrix[i, j]), 2) for j, k in enumerate(names)}
        iso_keys = [k for k in names if k.startswith("iso532_1")]
        entry = {
            "path": r["name"], "duration": round(r["duration"], 3), "channels": r["channels"],
            "strata": _strata(r), "eventDuration": round(r["eventDuration"], 3), "lowShare": round(r["lowShare"], 3),
            "tail": None if r["tail"] is None else round(r["tail"], 3), "events": r["events"],
            "asFile": r["asFile"], "gains": g,
            "spread": round(float(matrix[i].max() - matrix[i].min()), 2),
            "isoMinusMaxM": {lv.id: round(g[f"iso532_1.max@{lv.id}"] - g["momentaryMax"], 2) for lv in levels},
            "isoMinusIntegrated": {lv.id: round(g[f"iso532_1.max@{lv.id}"] - g["integrated"], 2) for lv in levels},
            "phonPerDb": {lv.id: (round((s[lv.id]["levelPhon"] - r["iso"][lv.id]["levelMax"]) / s[lv.id]["gainDb"], 2)
                                  if abs(s[lv.id]["gainDb"]) > 1.0 else None) for lv in levels},
            "converged": all(s[lv.id]["converged"] for lv in levels),
        }
        if len(levels) > 1:
            a, b = iso_keys[0], iso_keys[-1]
            entry["levelSensitivity"] = round(g[b] - g[a], 2)
        if not r["hasDocument"]:
            entry["note"] = "no-playhead-document"
        out_files.append(entry)

    def pair(a, b):
        d = _centre(gains[a] - gains[b])
        q = np.percentile(d, [5, 95])
        return {"a": a, "b": b, "range": round(float(d.max() - d.min()), 1), "p5to95": round(float(q[1] - q[0]), 1),
                "sd": round(float(d.std()), 2),
                "aWantsLouder": out_files[int(np.argmax(d))]["path"], "aWantsQuieter": out_files[int(np.argmin(d))]["path"]}

    pairs = [pair(a, b) for i, a in enumerate(names) for b in names[i + 1:]]
    doc = {
        "format": "listener-disagreement", "version": 1,
        "generator": {"name": "listener", "version": __version__},
        "created": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "implementations": implementations(None),
        "calibration": {"levels": [lv.describe() for lv in levels]},
        "conventions": {
            "gains": "dB each measure would give the file to make the corpus equally loud, corpus median removed",
            "ears": f"mono files: BS.1770 values +{MONO_AS_HEARD_DB:.2f} dB (heard in both ears); stereo files as measured",
            "operatingPoint": "ISO 532-1 runs on each file after bringing its Max M to the reference loudness of the calibration",
            "iso532_1": "gain solved so that every file's maximum loudness level equals the corpus median (phon): "
                        + ", ".join(f"{k} {v:.1f}" for k, v in targets.items()),
            "strata": {"duration": "of the loudest Playhead event (to its decay end); the file without a document",
                       "lowFrequency": f"at least {LOW_FREQUENCY_SHARE:.0%} of the power below {LOW_FREQUENCY_HZ:g} Hz",
                       "longTail": f"ISO 532-1 loudness stays above a quarter of its maximum for {LONG_TAIL_S:g} s or more after it"},
        },
        "measures": names,
        "pairs": pairs,
        "files": sorted(out_files, key=lambda e: -e["spread"]),
    }
    if pick:
        doc["stimuli"] = pick_stimuli(doc["files"], pick)
    return doc


def pick_stimuli(files: list[dict], count: int) -> list[dict]:
    """Spread the choice over the strata: the files where the measures part most, cell by cell."""
    cells: dict[tuple, list[dict]] = {}
    for f in files:
        s = f["strata"]
        cells.setdefault((s["duration"], s["lowFrequency"], s["longTail"]), []).append(f)
    for v in cells.values():
        v.sort(key=lambda e: -e["spread"])
    chosen, rank = [], 0
    while len(chosen) < min(count, len(files)):
        added = False
        for key in sorted(cells, key=lambda k: -cells[k][0]["spread"]):
            if rank < len(cells[key]) and len(chosen) < count:
                f = cells[key][rank]
                chosen.append({"path": f["path"], "cell": {"duration": key[0], "lowFrequency": key[1], "longTail": key[2]},
                               "spread": f["spread"], "rankInCell": rank + 1})
                added = True
        if not added:
            break
        rank += 1
    return chosen


def report_markdown(doc: dict) -> str:
    levels = [lv["id"] for lv in doc["calibration"]["levels"]]
    L = []
    L.append("# Where the measures disagree\n")
    L.append(f"{len(doc['files'])} files. Gains are in dB, corpus median removed: what each measure would give a file to "
             "make the corpus equally loud. A model stands in for nothing here; the report shows where the choice matters.\n")
    for lv in doc["calibration"]["levels"]:
        L.append(f"- `{lv['id']}`: {lv['text']}")
    L.append(f"- Ears: {doc['conventions']['ears']}.")
    L.append(f"- {doc['conventions']['operatingPoint']}.\n")
    L.append("## Pairs of measures\n")
    L.append("| Measure A | Measure B | Range (dB) | 5th to 95th percentile | A asks most gain for | A asks least gain for |")
    L.append("|---|---|---|---|---|---|")
    for p in sorted(doc["pairs"], key=lambda p: -p["p5to95"]):
        L.append(f"| {p['a']} | {p['b']} | {p['range']} | {p['p5to95']} | {p['aWantsLouder']} | {p['aWantsQuieter']} |")
    L.append("\n## Files, most disputed first\n")
    head = "| File | Event (s) | Class | Low | Tail (s) | Spread | " + " | ".join(f"ISO − Max M @{l}" for l in levels) + " | I − Max M | Peak − Max M |"
    L.append(head)
    L.append("|" + "---|" * (head.count("|") - 1))
    for f in doc["files"]:
        g = f["gains"]
        L.append(f"| {f['path']} | {f['eventDuration']} | {f['strata']['class'] or '–'} | {f['lowShare']:.2f} | {f['tail']} | "
                 f"{f['spread']} | " + " | ".join(f"{f['isoMinusMaxM'][l]:+.1f}" for l in levels)
                 + f" | {g['integrated'] - g['momentaryMax']:+.1f} | {g['peak'] - g['momentaryMax']:+.1f} |")
    if doc.get("stimuli"):
        L.append("\n## Proposed stimuli\n")
        L.append("| File | Duration | Low-frequency | Long tail | Spread (dB) |")
        L.append("|---|---|---|---|---|")
        for s in doc["stimuli"]:
            c = s["cell"]
            L.append(f"| {s['path']} | {c['duration']} | {'yes' if c['lowFrequency'] else 'no'} | {'yes' if c['longTail'] else 'no'} | {s['spread']} |")
    return "\n".join(L) + "\n"
