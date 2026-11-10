# SPDX-License-Identifier: Apache-2.0
"""The numbers quoted in docs/FIRST_CHECKS.md, from the files tools/first_checks.sh writes.

usage: python tools/summarise.py <out folder> <playhead checkout>
Reads conformance.json, sfx56.listener-measures.json, disagreement.json, phenomena.json, and, if present,
playhead-sone.json (node tools/playhead_sone.js <playhead> <sfx> > out/playhead-sone.json).
"""
import json
import os
import sys

import numpy as np

out, playhead = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)


def load(name):
    p = os.path.join(out, name)
    return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else None


def centre(v):
    v = np.asarray(v, float)
    return v - np.median(v)


def spread(v):
    v = centre(v)
    q = np.percentile(v, [5, 95])
    return f"range {v.max() - v.min():.1f} dB, 5th to 95th percentile {q[1] - q[0]:.1f} dB"


conf = load("conformance.json")
if conf:
    print("## Conformance")
    suites = {}
    for c in conf["cases"]:
        suites.setdefault(c["suite"], []).append(c)
    for s, cs in suites.items():
        ran = [c for c in cs if c.get("pass") is not None]
        dev = [abs(c["worstDeviation"]) for c in ran if isinstance(c.get("worstDeviation"), (int, float))]
        print(f"- {s}: {sum(c['pass'] for c in ran)} of {len(ran)} passed, {len(cs) - len(ran)} skipped"
              + (f"; largest deviation {max(dev):.3f}" if dev else ""))
    iso = [c for c in conf["cases"] if c["suite"] == "iso532-1" and c.get("pass") is not None]
    if iso:
        print("- ISO 532-1 largest Nmax error: %.4f sone; N(t) inside the 5 %% band for at least %.2f %% of the time"
              % (max(abs(c["measured"]["nMax"] - c["expected"]["nMax"]) for c in iso), 100 * min(c["within5Percent"] for c in iso)))
        bad = [c for c in iso if not c["n5Reproduced"]]
        print("- N5 not reproduced by any trimming rule for signals:", [c["case"] for c in bad])
        for c in iso:
            if c["case"] in (10, 11, 12, 13, 18):
                print(f"    signal {c['case']}: standard {c['expected']['n5']:.3f}; by rule {c['n5ByRule']}")
    din = [c for c in conf["cases"] if c["suite"] == "din45692"]
    if din:
        print("- DIN 45692 per-frame median inside tolerance for %d of %d; largest per-frame deviation %.3f acum"
              % (sum(c["perFramePass"] for c in din), len(din), max(abs(c["perFrameMedian"] - c["expected"]) for c in din)))
    for c in conf["cases"]:
        if c["suite"] == "reference-tones":
            print(f"    {c['case']}: {c.get('measured', c.get('skipped'))}")

meas = load("sfx56.listener-measures.json")
if meas:
    print("\n## Measures on the corpus")
    files = [f for f in meas["files"] if "spans"in f]
    par = {}
    for f in files:
        for k, v in ((f.get("playhead") or {}).get("listenerMinusPlayhead") or {}).items():
            par.setdefault(k, []).append(v)
    for k, v in par.items():
        print(f"- listener minus Playhead, {k}: median {np.median(v):+.2f} dB, largest {max(v, key=abs):+.2f} dB over {len(v)} files")
    lv = meas["calibration"]["levels"][-1]["id"]
    sp = {f["path"]: next(s for s in f["spans"] if s["id"] == "file") for f in files}
    zw = np.array([sp[p]["byLevel"][lv]["iso532_1"]["levelMax"] for p in sp])
    for key in ("integrated", "momentaryMax", "shortTermMax", "peak", "rms"):
        m = np.array([sp[p]["bs1770"][key] for p in sp])
        print(f"- as the earlier pilot computed it (phon minus {key}, files as stored, {lv}): {spread(zw - m)}")
    old = os.path.join(playhead, "experiments/levels/measures.json") if playhead else None
    if old and os.path.isfile(old):
        R = json.load(open(old))
        for key in ("lufs_i", "lufs_m"):
            print(f"- the earlier pilot's own file (zw_max minus {key}): {spread([r['zw_max'] - r[key] for r in R])}")
        by = {r["file"]: r for r in R}
        common = [p for p in sp if os.path.basename(p) in by]
        d = np.array([sp[p]["byLevel"][lv]["iso532_1"]["levelMax"] - by[os.path.basename(p)]["zw_max"] for p in common])
        print(f"- listener's ISO 532-1 level minus the earlier pilot's, per file: median {np.median(d):+.2f} phon, from {d.min():+.2f} to {d.max():+.2f} (mean of two ears against a mono mix)")
        d = np.array([sp[p]["bs1770"]["momentaryMax"] - by[os.path.basename(p)]["lufs_m"] for p in common])
        print(f"- listener's Max M minus the earlier pilot's: median {np.median(d):+.2f} dB, from {d.min():+.2f} to {d.max():+.2f}")
    ps = load("playhead-sone.json")
    if ps:
        names = [p for p in sp if os.path.basename(p) in ps]
        full = np.array([sp[p]["byLevel"][lv]["iso532_1"]["nMax"] for p in names])
        simple = np.array([ps[os.path.basename(p)]["nMax"] for p in names])
        ratio = 10 * np.log2(simple / full)  # in phon, doubling per 10
        rank = np.corrcoef(np.argsort(np.argsort(full)), np.argsort(np.argsort(simple)))[0, 1]
        print(f"- Playhead's simplified loudness against the full method (maximum, {lv}): {np.median(simple / full):.2f} times the sone "
              f"(median), that is {np.median(ratio):+.1f} phon; after removing that offset {spread(ratio)}; rank correlation {rank:.2f}")
        full5 = np.array([sp[p]["byLevel"][lv]["iso532_1"]["n5"] for p in names])
        simple5 = np.array([ps[os.path.basename(p)]["n5"] for p in names])
        r5 = 10 * np.log2(simple5 / full5)
        rank5 = np.corrcoef(np.argsort(np.argsort(full5)), np.argsort(np.argsort(simple5)))[0, 1]
        print(f"- the same for the 95th percentile over the file: {np.median(simple5 / full5):.2f} times the sone, {np.median(r5):+.1f} phon; "
              f"after removing that offset {spread(r5)}; rank correlation {rank5:.2f}; Playhead's calibration constant kN = {ps[os.path.basename(names[0])]['kN']:.2f}")
        worst = np.argsort(centre(ratio))
        print("    most under:", [(os.path.basename(names[i]), round(float(centre(ratio)[i]), 1)) for i in worst[:3]],
              "most over:", [(os.path.basename(names[i]), round(float(centre(ratio)[i]), 1)) for i in worst[-3:]])
    ecma = [(sp[p]["byLevel"][lv].get("ecma418_2"), sp[p]["byLevel"][lv]["iso532_1"]) for p in sp]
    ecma = [(e, z) for e, z in ecma if e]
    if ecma:
        d = [40 + 10 * np.log2(max(e["loudnessMax"], 1e-6)) - z["levelMax"] for e, z in ecma]
        print(f"- ECMA-418-2 maximum against ISO 532-1 maximum, as loudness levels ({len(ecma)} files): {spread(d)}")
        st = [e["standardSingleValues"]["loudnessPowAvg"] / e["loudnessMax"] for e, _ in ecma if "standardSingleValues" in e]
        print(f"- ECMA-418-2's own single value over the maximum: median {np.median(st):.2f}, from {min(st):.2f} to {max(st):.2f}")

dis = load("disagreement.json")
if dis:
    print("\n## Disagreement")
    print("-", dis["conventions"]["iso532_1"])
    for p in dis["pairs"]:
        if "iso532_1" in p["a"] + p["b"] and ("momentaryMax" == p["a"] or "integrated" == p["a"] or "iso" in p["a"]):
            print(f"- {p['a']} against {p['b']}: range {p['range']} dB, 5th to 95th {p['p5to95']} dB; most gain {p['aWantsLouder']}, least {p['aWantsQuieter']}")
    for a, b in (("integrated", "momentaryMax"), ("peak", "integrated"), ("peak", "shortTermMax"), ("momentaryMax", "momentaryMax@event")):
        p = next(p for p in dis["pairs"] if p["a"] == a and p["b"] == b)
        print(f"- {a} against {b}: range {p['range']} dB, 5th to 95th {p['p5to95']} dB")
    for p in dis["pairs"]:
        if "iso532_1" in p["b"] and "iso532_1" not in p["a"]:
            print(f"    spread of the ISO 532-1 gain left after normalising with {p['a']} ({p['b'].split('@')[1]}): SD {p['sd']} dB")
    F = dis["files"]
    if "levelSensitivity" in F[0]:
        ls = np.array([f["levelSensitivity"] for f in F])
        print(f"- change of the ISO 532-1 gain between the two levels: from {ls.min():+.2f} to {ls.max():+.2f} dB, standard deviation {ls.std():.2f}")
    ppd = [v for f in F for v in f["phonPerDb"].values() if v is not None]
    print(f"- phon per dB of gain over the files: from {min(ppd):.2f} to {max(ppd):.2f}")
    mono = [f for f in F if f["channels"] == 1]
    print(f"- mono files: {len(mono)} of {len(F)} (each +3.01 dB in BS.1770 as heard)")
    print("- stimuli picked:", ", ".join(s["path"].replace(".flac", "") for s in dis.get("stimuli", [])))

ph = load("phenomena.json")
if ph:
    print("\n## Phenomena")
    for m, s in ph["score"].items():
        print(f"- {m}: agrees on {s['agrees']}, near on {s['near']}, of {s['of']}")
