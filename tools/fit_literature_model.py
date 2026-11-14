# SPDX-License-Identifier: Apache-2.0
"""Fit the literature model on the fit set, test it on the held-out set, and write the results.

usage: python tools/fit_literature_model.py [out folder]     (default: results/literature-model)
The sets are those of docs/LITERATURE_SPLIT.md. Writes fit.json, and src/listener/model/fitted.py with the values.
"""
import json
import os
import sys
from dataclasses import asdict, replace

import numpy as np
from scipy.optimize import least_squares, brentq

from listener.model import literature as M
from listener.phenomena import bench as B

out = sys.argv[1] if len(sys.argv) > 1 else "results/literature-model"
os.makedirs(out, exist_ok=True)
SEED = B.RNG_SEED


def pair(a, b, shelf=0.0):
    return M.track(a, shelf), M.track(b, shelf)


def fit_items():
    ramp = B.level_ramp_tone(60.0, 75.0)
    burst = B.decaying(B.noise(0.05, seed=SEED + 3), 80.0, 1.0, 40.0)
    return {
        "F1": dict(what="1 kHz tone, 5 against 200 ms, 56 dB SPL", lo=18, hi=19, ab=(B.tone_burst(56, .2), B.tone_burst(56, .005))),
        "F2": dict(what="the same, 100 dB SPL", lo=9, hi=11, ab=(B.tone_burst(100, .2), B.tone_burst(100, .005))),
        "F3": dict(what="noise, 5 against 200 ms, 76 dB SPL", lo=18, hi=19, ab=(B.noise_burst(76, .2, seed=SEED + 1), B.noise_burst(76, .005, seed=SEED + 2))),
        "F4": dict(what="the same, 100 dB SPL", lo=12, hi=14, ab=(B.noise_burst(100, .2, seed=SEED + 1), B.noise_burst(100, .005, seed=SEED + 2))),
        "F5": dict(what="1 kHz tone, 30 against 200 ms, 56 dB SPL", lo=6, hi=8, ab=(B.tone_burst(56, .2), B.tone_burst(56, .03))),
        "F6": dict(what="1 kHz tone falling against rising 15 dB", lo=3.1, hi=5.3, ab=(ramp, ramp[::-1].copy())),
        "F7": dict(what="impulses 4 s apart against one", lo=-1, hi=1, ab=(burst, B.train(burst, 4.0, 3))),
    }


def lf_pair():
    return (B._ramp(B._amp(75.0) * B.noise(4.0, 707.0, 1414.0, pink=True, seed=SEED + 4), 20.0),
            B._ramp(B._amp(75.0) * B.noise(4.0, 44.5, 89.0, pink=True, seed=SEED + 4), 20.0))


def held_out(p):
    """Predictions for the held-out set."""
    rows = {}
    long_levels = np.arange(15.0, 70.1, 5.0)
    for key, short, published in (("H1", 0.050, "about 9"), ("H2", 0.010, "about 22"), ("H3", 0.002, "about 40")):
        vals = [M.matching_gain(*pair(B.tone_burst(L, .25, 5000.0, 2.0), B.tone_burst(L, short, 5000.0, 2.0)), p) for L in long_levels]
        i = int(np.argmax(vals))
        rows[key] = dict(what=f"5 kHz tone, {short * 1000:g} against 250 ms, most integration over level", published=published,
                         predicted=round(max(vals), 1), atLevel=float(long_levels[i]),
                         byLevel={f"{L:g}": round(v, 1) for L, v in zip(long_levels, vals)})
    rows["H4"] = dict(what="5 kHz tone, 2 against 250 ms, 60 dB above threshold (63 dB SPL)", published="20 to 25",
                      predicted=round(M.matching_gain(*pair(B.tone_burst(63, .25, 5000.0, 2.0), B.tone_burst(63, .002, 5000.0, 2.0)), p), 1))
    tone = np.sin(2 * np.pi * 1000 * np.arange(int(0.25 * B.SR)) / B.SR)
    for key, name, carrier in (("H5", "tone", tone), ("H6", "noise", B.noise(0.25, seed=SEED + 5))):
        fs = B.decaying(carrier, 75.0, 2.0, 40.0)
        rows[key] = dict(what=f"reversed envelope against impact-like one, {name}", published="negative (reverse louder); -1 to -3 from one listener",
                         predicted=round(M.matching_gain(*pair(fs, fs[::-1].copy()), p), 1))
    burst = B.decaying(B.noise(0.05, seed=SEED + 3), 80.0, 1.0, 40.0)
    rows["H7"] = dict(what="impulses 0.2 s apart against one", published="negative (train louder)",
                      predicted=round(M.matching_gain(*pair(burst, B.train(burst, 0.2, 10)), p), 1))
    return rows


items = fit_items()
tracks = {k: pair(*v["ab"]) for k, v in items.items()}
keys = list(items)
target = np.array([(items[k]["lo"] + items[k]["hi"]) / 2 for k in keys])
half = np.array([max((items[k]["hi"] - items[k]["lo"]) / 2, 1.0) for k in keys])


def predict(p, which=keys):
    return np.array([M.matching_gain(*tracks[k], p) for k in which])


def fit(base, free, which=keys):
    idx = [keys.index(k) for k in which]
    bounds = {"beta": (0.1, 1.0), "t_half": (0.01, 0.6), "kappa": (0.0, 4.0), "q": (1.2, 12.0)}
    x0 = [getattr(base, n) for n in free]

    def resid(x):
        p = replace(base, **dict(zip(free, x)))
        return (predict(p, which) - target[idx]) / half[idx]
    if not free:
        return base, float(np.sqrt((resid([]) ** 2).mean()))
    r = least_squares(resid, x0, bounds=([bounds[n][0] for n in free], [bounds[n][1] for n in free]), diff_step=0.02)
    return replace(base, **dict(zip(free, [float(v) for v in r.x]))), float(np.sqrt((r.fun ** 2).mean()))


def fit_shelf(p):
    a, b = lf_pair()
    ta = None

    def miss(g):
        return M.matching_gain(*pair(a, b, g), replace(p, shelf_db=g)) - 9.98
    lo, hi = miss(-20.0), miss(0.0)
    return float(brentq(miss, -20.0, 0.0, xtol=0.05)) if lo * hi < 0 else (0.0 if abs(hi) < abs(lo) else -20.0)


def miss_of(value, lo, hi):
    return round(float(value - hi if value > hi else (value - lo if value < lo else 0.0)), 2)


# ---- the fit
FREE = ["beta", "t_half"]
start = M.Params(beta=0.5, t_half=0.08)
best, rms = fit(start, FREE)
best = replace(best, shelf_db=fit_shelf(best))
pred = predict(best)
a, b = lf_pair()
f8 = M.matching_gain(*pair(a, b, best.shelf_db), best)

doc = {"format": "listener-literature-fit", "version": 1, "model": "L0",
       "parameters": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in asdict(best).items()},
       "fitted": FREE + ["shelf_db"], "fitRms": round(rms, 3),
       "fit": {k: dict(what=items[k]["what"], published=[items[k]["lo"], items[k]["hi"]], predicted=round(float(v), 1),
                       miss=miss_of(v, items[k]["lo"], items[k]["hi"])) for k, v in zip(keys, pred)}}
doc["fit"]["F8"] = dict(what="63 Hz octave band against 1 kHz octave band, 75 dB SPL", published=[9, 11], predicted=round(f8, 1), miss=miss_of(f8, 9, 11))

# ---- leave one result out: fit on the others, predict the one left out
loo = {}
for k in keys:
    others = [x for x in keys if x != k]
    p_k, _ = fit(start, FREE, others)
    v = float(M.matching_gain(*tracks[k], p_k))
    loo[k] = dict(predicted=round(v, 1), miss=miss_of(v, items[k]["lo"], items[k]["hi"]),
                  parameters={n: round(getattr(p_k, n), 3) for n in FREE})
doc["leaveOneOut"] = loo

# ---- what each part buys: switch it off, refit the rest, score the fit set
abl = {}
for name, base, free in (
        ("full model", start, FREE),
        ("loudness doubles every 10 dB at all levels", replace(start, loudness="power"), FREE),
        ("loudness formed per critical band and summed", replace(start, bands=True), FREE),
        ("with decay suppression (one more parameter)", replace(start, kappa=0.7), FREE + ["kappa"]),
        ("growth with duration as a plain power law (no saturation before 3 s)", replace(start, t_half=1e9), ["beta"]),
        ("a level-dominant mean instead of the maximum (one more parameter)", replace(start, q=3.0), FREE + ["q"])):
    p_a, rms_a = fit(base, free)
    v = predict(p_a)
    abl[name] = dict(rms=round(rms_a, 2), worst=round(float(np.abs((v - target)).max()), 1),
                     within1=int(sum(abs(miss_of(x, items[k]["lo"], items[k]["hi"])) <= 1.0 for k, x in zip(keys, v))),
                     predictions={k: round(float(x), 1) for k, x in zip(keys, v)},
                     parameters={n: round(getattr(p_a, n), 3) for n in FREE + ["kappa", "q"]})
doc["ablations"] = abl

doc["heldOut"] = held_out(best)


def others(a, b):
    """Max M and the ISO 532-1 maximum for a pair, as the benchmark computes them."""
    pr = B.predictions(a, b, None)
    return {"momentaryMax": pr["momentaryMax"], "iso532_1.max": pr["iso532_1.max"]}


cmp_rows = {"F5": others(*items["F5"]["ab"])}
for key, short in (("H1", 0.050), ("H2", 0.010), ("H3", 0.002)):
    per = [others(B.tone_burst(L, .25, 5000.0, 2.0), B.tone_burst(L, short, 5000.0, 2.0)) for L in (25.0, 45.0, 65.0)]
    cmp_rows[key] = {m: max(v[m] for v in per if v[m] is not None) for m in per[0]}
cmp_rows["H4"] = others(B.tone_burst(63, .25, 5000.0, 2.0), B.tone_burst(63, .002, 5000.0, 2.0))
doc["otherMeasures"] = cmp_rows
with open(os.path.join(out, "fit.json"), "w", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=1)
with open(os.path.join(os.path.dirname(M.__file__), "fitted.py"), "w", encoding="utf-8") as fh:
    fh.write('# SPDX-License-Identifier: Apache-2.0\n"""Written by tools/fit_literature_model.py: the fitted values of the literature model L0."""\n')
    fh.write("FITTED_VALUES = " + json.dumps({k: doc["parameters"][k] for k in FREE + ["shelf_db"]}) + "\n")
print(json.dumps({k: doc[k] for k in ("parameters", "fitRms")}))
for k, v in doc["fit"].items():
    print(k, v["published"], v["predicted"], v["miss"])
print("leave one out:", {k: (v["predicted"], v["miss"]) for k, v in loo.items()})
for k, v in abl.items():
    print("ablation:", k, v["rms"], v["within1"], v["parameters"], v["predictions"])
for k, v in doc["heldOut"].items():
    print(k, v["published"], "->", v["predicted"], v.get("atLevel", ""))
print("other measures:", cmp_rows)
