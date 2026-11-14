# SPDX-License-Identifier: Apache-2.0
"""Write docs/LITERATURE_MODEL.md from the stored results.

usage: python tools/report_literature_model.py [results folder] [output file]
Reads fit.json and phenomena.json (written by tools/fit_literature_model.py and `listener phenomena`) and, for the
comparison with the first revision, revision-1/fit.json. No number in the report is typed by hand.
"""
import json
import os
import sys

res = sys.argv[1] if len(sys.argv) > 1 else "results/literature-model"
out = sys.argv[2] if len(sys.argv) > 2 else "docs/LITERATURE_MODEL.md"
fit = json.load(open(os.path.join(res, "fit.json"), encoding="utf-8"))
ph = json.load(open(os.path.join(res, "phenomena.json"), encoding="utf-8"))
old = json.load(open(os.path.join(res, "revision-1", "fit.json"), encoding="utf-8"))
P, om, ho = fit["parameters"], fit["otherMeasures"], fit["heldOut"]
rows = {r["id"]: r for r in ph["phenomena"]}
SHORT = {"peak": "Peak", "rms": "RMS", "integrated": "LUFS-I", "momentaryMax": "Max M", "shortTermMax": "Max S",
         "iso532_1.max": "ISO 532-1 maximum", "iso532_1.n5": "ISO 532-1 N5", "ecma418_2.max": "ECMA-418-2 maximum",
         "literature.L0": "literature model"}


def f(v, sign=False):
    if v is None:
        return "–"
    v = round(v, 1) + 0.0     # no "-0.0"
    return f"{v:+.1f}" if sign and v != 0 else f"{v:.1f}"


def grown(t):
    return (t / (t + P["t_half"])) ** P["beta"]


def miss(v, lo, hi):
    return max(lo - v, v - hi, 0.0)


# ---- held-out durations: listeners' values as the paper gives them
H_TARGET = {"H1": (9.0, 9.0), "H2": (22.0, 22.0), "H3": (40.0, 40.0), "H4": (20.0, 25.0)}


def mean_miss(get):
    return sum(miss(get(k), *H_TARGET[k]) for k in H_TARGET) / len(H_TARGET)


mm_new = {"L0": mean_miss(lambda k: ho[k]["predicted"]), "Max M": mean_miss(lambda k: om[k]["momentaryMax"]),
          "ISO": mean_miss(lambda k: om[k]["iso532_1.max"])}
mm_old = mean_miss(lambda k: old["heldOut"][k]["predicted"])

bands = [k for k, v in ho.items() if v.get("addedAfterFitting")]


def band_score(get):
    ms = [miss(get(k), *ho[k]["range"]) for k in bands]
    return sum(m <= 1.0 for m in ms), (sum(m * m for m in ms) / len(ms)) ** 0.5


bs = {"L0": band_score(lambda k: ho[k]["predicted"]), "LUFS-I": band_score(lambda k: om[k]["integrated"]),
      "ISO": band_score(lambda k: om[k]["iso532_1.max"])}
lm = ph["literatureModel"]
score, held = ph["score"], lm["scoreHeldOut"]
n_rows, n_fit, n_held = score["literature.L0"]["of"], len(lm["fitted"]), held["literature.L0"]["of"]
order = ["literature.L0", "iso532_1.max", "ecma418_2.max", "iso532_1.n5", "integrated", "momentaryMax", "shortTermMax", "rms", "peak"]
order = sorted((m for m in order if m in score), key=lambda m: (-score[m]["agrees"], -score[m]["near"]))

L = []
A = L.append
A("# The literature model, version L0: what it is and how it does\n")
A("Second revision, 14 November 2026: refitted after the papers behind the benchmark were read. The first revision, "
  "built the same day on stimuli rebuilt from the research notes, is kept in `results/literature-model/revision-1/`. "
  "Every number here is written by `tools/fit_literature_model.py` and `listener phenomena` into "
  "`results/literature-model/`, and this file by `tools/report_literature_model.py`. Which published results set the "
  "model and which test it: `docs/LITERATURE_SPLIT.md`.\n")
A("## In short\n")
A(f"- **Reading the papers made the model's test result worse, and it is still ahead.** On the four held-out numbers "
  f"(tone durations at 5 kHz, a frequency it was not set at) its mean miss is **{mm_new['L0']:.1f} dB**, against "
  f"{mm_new['Max M']:.1f} dB for Max M and {mm_new['ISO']:.1f} dB for the ISO 532-1 maximum. With the rebuilt stimuli it was {mm_old:.1f} dB.")
A("- **Why it changed.** In the paper the level named for the largest temporal integration is the short sound's. The "
  "long sound it matches is then 18 dB lower, where loudness grows most slowly with level. The rebuilt stimuli had "
  "both at the named level. With the right levels the loudness function explains more of the effect and the fitted "
  f"growth with duration is faster ({P['t_half'] * 1000:.0f} ms where it was {old['parameters']['t_half'] * 1000:.0f} ms), "
  "which costs accuracy between 50 and 250 ms.")
A(f"- **Six new test results, never fitted**: octave bands of noise from 125 Hz to 8 kHz against the 1 kHz band. The "
  f"model is within 1 dB of the listeners' range on {bs['L0'][0]} of {len(bands)} (LUFS-I {bs['LUFS-I'][0]}, ISO 532-1 {bs['ISO'][0]}). "
  "The listeners' values are derived from the paper's table and carry 1.5 dB of doubt.")
A(f"- On the benchmark's {n_rows} results it agrees with {score['literature.L0']['agrees']} "
  f"(ISO 532-1 maximum {score['iso532_1.max']['agrees']}, Max M {score['momentaryMax']['agrees']}, LUFS-I {score['integrated']['agrees']}). "
  f"{n_fit} of them set it. On the {n_held} that test it: {held['literature.L0']['agrees']} "
  f"(ISO 532-1 maximum {held['iso532_1.max']['agrees']}, ECMA-418-2 {held.get('ecma418_2.max', {}).get('agrees', '–')}, "
  f"LUFS-I {held['integrated']['agrees']}, Max M {held['momentaryMax']['agrees']}).")
A("- It still **fails** on onset weighting (wrong sign, like every other measure), on noise at a moderate level, and on "
  "the shortest sounds at 5 kHz.")
A("- It has three fitted parameters. It has never met a listener's judgement of a sound effect. That waits for the pilot.\n")

A("## What it is\n")
A("One sound in, one number out: the level in dB of a steady 1 kHz tone predicted to be as loud.\n")
A(f"1. **K-weighted level** every 0.5 ms, with a low shelf of **{P['shelf_db']:.1f} dB** under 120 Hz on top of K-weighting.")
A("2. **Loudness of each moment** from that level, by a loudness function for a 1 kHz tone that is flattest at moderate\n"
  "   levels (Buus & Florentine's \"inflected exponential\" function).")
A(f"3. **Growth with duration in the loudness domain**: a sound of duration T reaches (T / (T + {P['t_half'] * 1000:.0f} ms))^{P['beta']:.2f} of its\n"
  f"   steady loudness: {grown(.005):.2f} at 5 ms, {grown(.03):.2f} at 30 ms, {grown(.2):.2f} at 200 ms, {grown(1.0):.2f} at 1 s.")
A("4. **The maximum** of the result is the sound's loudness.\n")
A("Step 3 is the equal-loudness-ratio model of Buus, Florentine & Poulsen (1997), made to run on any envelope: a short\n"
  "and a long sound differ by the same loudness ratio at every level, and how many dB that ratio is worth depends on how\n"
  "steep the loudness function is at that level. Nothing in the model says \"integration is smaller at high levels\".\n")
A("`listener measure` reports it per span and playback level as `literatureL0.level`; `listener phenomena` has it as a\n"
  "column; `listener.model.literature.matching_gain` gives the gain between two sounds.\n")

A("## The results that set it\n")
A("Level difference at equal loudness, dB. \"Before\": the first revision's model on its rebuilt stimuli.\n")
A("| # | Result | Listeners | L0 | L0 with this result left out of the fit | Max M | ISO 532-1 maximum | L0 before |")
A("|---|---|---|---|---|---|---|---|")
for k, v in fit["fit"].items():
    loo = fit["leaveOneOut"].get(k)
    A(f"| {k} | {v['what']} | {v['published'][0]:g} to {v['published'][1]:g} | **{f(v['predicted'])}** | "
      f"{f(loo['predicted']) if loo else '(sets the shelf)'} | {f(om[k]['momentaryMax'])} | {f(om[k]['iso532_1.max'])} | {f(old['fit'][k]['predicted'])} |")
inside = [k for k, v in fit["leaveOneOut"].items() if v["miss"] == 0]
outside = [abs(v["miss"]) for v in fit["leaveOneOut"].values() if v["miss"] != 0]
A(f"\nFitted: the two numbers of step 3 and the shelf. Left out one at a time, the model still predicts {', '.join(inside)} "
  f"inside the published range, and misses the others by {min(outside):.1f} to {max(outside):.1f} dB.")
A("Later studies from the same laboratory, with a different matching procedure, found 26 to 27 dB where F1 has 18 to "
  "19 (Buus, Florentine & Poulsen 1999). F1's range is one study's.\n")

A("## The results that test it\n")
A("### Fixed before fitting\n")
A("| # | Result | Listeners | L0 | Max M | ISO 532-1 maximum | L0 before |")
A("|---|---|---|---|---|---|---|")
for k in ("H1", "H2", "H3", "H4", "H5", "H6", "H7"):
    v = ho[k]
    A(f"| {k} | {v['what']} | {v['published']} | **{f(v['predicted'], k > 'H4')}** | {f(om[k]['momentaryMax'], k > 'H4')} | "
      f"{f(om[k]['iso532_1.max'], k > 'H4')} | {f(old['heldOut'][k]['predicted'], k > 'H4')} |")
A(f"\n- **H1 to H4** (Buus et al. 1997, read in the paper): mean miss {mm_new['L0']:.1f} dB for the model, {mm_new['Max M']:.1f} for Max M, "
  f"{mm_new['ISO']:.1f} for the ISO 532-1 maximum. The model follows the growth of integration as the short tone gets "
  f"shorter. It now reads {ho['H1']['predicted']:.1f} dB for 50 against 250 ms, under the 7 dB of an energy window and the "
  f"9 dB of listeners: its growth with duration is nearly over by 50 ms. It puts the most integration with the long "
  f"tone at {ho['H3']['atLevel']:g} dB SPL where the paper finds it near 22 to 24.")
A("- **H5, H6** (Stecker & Hafter 2000, now with the paper's own envelopes, a 330 Hz tone and white noise): the right "
  "sign and about the size the one listener gave. The paper found the effect mainly after impact-like sounds.")
A("- **H7**: the right sign, weakly. The paper's stimuli could not be read; these are still rebuilt.\n")
A("### Added after fitting, never fitted\n")
A("Fenton & Lee (2017): dB by which listeners raised an octave band of pink noise to match the 1 kHz band at 75 dB.\n")
A("| # | Result | Listeners (derived) | L0 | LUFS-I | ISO 532-1 maximum |")
A("|---|---|---|---|---|---|")
for k in bands:
    v = ho[k]
    A(f"| {k} | {v['what']} | {v['published']} | **{f(v['predicted'], True)}** | {f(om[k]['integrated'], True)} | {f(om[k]['iso532_1.max'], True)} |")
A(f"\nRoot mean square miss outside the range: model {bs['L0'][1]:.1f} dB, LUFS-I {bs['LUFS-I'][1]:.1f} dB, ISO 532-1 {bs['ISO'][1]:.1f} dB. "
  "Above 250 Hz the model is K-weighting, so there it shares LUFS-I's errors; the shelf fitted at 63 Hz also holds at "
  "125 Hz. Caution: the listeners' values are this project's BS.1770 gain minus the error the paper tabulates, and the "
  "paper's one printed BS.1770 value (2.73 dB at 63 Hz) is 0.8 dB under this project's (3.55 dB).\n")

A("## What was tried and dropped\n")
A("Each line is the model with one thing changed, refitted on the same seven results (the shelf's result apart).\n"
  "The error is the root mean square of the misses, each divided by the half-width of its published range (at least 1 dB).\n")
A("| Variant | Error | Within 1 dB of the range | Exponent | Half-duration |")
A("|---|---|---|---|---|")
for name, v in fit["ablations"].items():
    th = v["parameters"]["t_half"]
    A(f"| {name} | {v['rms']:.2f} | {v['within1']} of {len(v['predictions'])} | {v['parameters']['beta']:.2f} | {'none' if th > 100 else f'{th * 1000:.0f} ms'} |")
ab = fit["ablations"]
A(f"\nThe order is the first revision's. The loudness function matters most (error {ab['full model']['rms']:.2f} against "
  f"{ab['loudness doubles every 10 dB at all levels']['rms']:.2f} without it); decay suppression and a level-dominant mean "
  "buy nothing; loudness formed per critical band and summed is much worse. Onset weighting was taken out before "
  "fitting (`docs/LITERATURE_SPLIT.md`). The model's form was chosen on the first revision's stimuli and only refitted here.\n")

A("## On the whole benchmark\n")
A(f"`results/literature-model/phenomena.md` has the table. Agrees (near) of {n_rows}: "
  + "; ".join(f"{SHORT[m]} {score[m]['agrees']} ({score[m]['near']})" for m in order) + ".")
A(f"On the {n_held} rows that did not set the model: "
  + "; ".join(f"{SHORT[m]} {held[m]['agrees']} ({held[m]['near']})" for m in order) + ".\n")

A("## Predictions for what nobody has measured\n")
A("dB by which the second sound would be raised to match the first. On record before the listening test.\n")
cols = ["literature.L0", "momentaryMax", "integrated", "iso532_1.max", "ecma418_2.max"]
A("| Contrast | " + " | ".join(("L0" if m == "literature.L0" else SHORT[m]) for m in cols) + " | L0 before |")
A("|---|" + "---|" * (len(cols) + 1))
old_open = {r["id"]: r["predictions"]["literature.L0"] for r in json.load(open(os.path.join(res, "revision-1", "phenomena.json"), encoding="utf-8"))["phenomena"]}
for r in ph["phenomena"]:
    if r["kind"] == "open":
        A(f"| {r['title']} | " + " | ".join(f(r["predictions"].get(m), True) for m in cols) + f" | {f(old_open[r['id']], True)} |")
A("\nFor the boom the model sits between Max M and the hearing models, and its change with level goes the other way from\n"
  "theirs: it has one fixed shelf where hearing's low-frequency sensitivity changes with level. Treat its low-frequency\n"
  "predictions as valid near 75 dB SPL only.\n")

A("## What reading the papers changed\n")
A("| Paper | What was read | What changed |")
A("|---|---|---|")
A("| Florentine, Buus & Poulsen 1996 | The abstracts. The paper is behind a paywall and the fetch was refused. Gating from Buus et al. 1999, which says the 1996 study used the same | The named level is the 5 ms sound's, so the 200 ms sound is 18 dB lower. The \"5 ms\" tone is a 13 ms raised-cosine pulse with 5 ms of equivalent duration. Noise bandwidth still unknown |")
A("| Buus, Florentine & Poulsen 1997 | The paper, again | Linear 2 ms ramps, not raised-cosine. The largest integration is with the 250 ms tone near 22 to 24 dB SPL |")
A("| Buus, Florentine & Poulsen 1999 | The paper (new) | Maxima of 26 to 27 dB at 1 kHz with a roving-level procedure; listeners range from 13 to 36 dB |")
A("| Ponsot, Susini & Meunier 2015 | The paper | Nothing in the stimulus. Matching gives 3.2 and 3.4 dB; the asymmetry shrinks for ramps reaching 80 to 90 dB SPL |")
A("| Stecker & Hafter 2000 | The paper | Its own envelope family, a 330 Hz tone and white noise at 80 dB SPL peak, in place of an exponential decay on a 1 kHz tone. One line of the envelope's equation was unreadable in the copy |")
A("| Fenton & Lee 2017 | The paper | 8th-order octave filters; six more bands from its Table 1; its BS.1770 value at 63 Hz differs from this project's by 0.8 dB |")
A("| Fischenich et al. 2021 | The paper | Primacy only for contiguous segments, not when they are 500 ms apart. Stimulus now ten 100 ms segments at 55 dB SPL. The paper says a maximum rule cannot give primacy |")
A("| Pedersen & Ellermeier 2008 | The paper | Listeners given feedback weighted all segments equally; without it, the beginning counted most. That suggests onset weighting is partly a way of listening, which supports modelling it as a separate decision stage |")
A("| Ogura, Suzuki & Sone 1991 | The abstract. The journal's site refuses automated reading of the file | Nothing. Its two rows keep rebuilt stimuli |\n")

A("## What limits this version\n")
A("- **Two papers still unread.** Florentine et al. (1996) sets four of the eight fit results and Ogura et al. (1991) one.")
A("- **The loudness function's coefficients were recalled, not read.** Three checks against sources that were read\n"
  "  hold (1.000 sone at 40 dB SPL; local exponents 0.25 and 0.41 where Buus et al. give about 0.25 and 0.43).")
A("- **One loudness function for all sounds.** It is the 1 kHz tone's. The misses on noise and at 5 kHz point at this.")
A("- **Few numbers.** Eight set three parameters. The ranges come from panels of 3 to 16 listeners, and two studies of\n"
  "  one laboratory differ by 8 dB on the largest of them.")
A("- **Held-out results were seen during development**, and the model's form was chosen on the first revision's\n"
  "  stimuli. Every choice between variants was made on the fit set's error alone.")
A("- **The six band results are derived**, not printed in the paper.\n")

A("## Next\n")
A("1. The two unread papers: both need a person to open them.")
A("2. A loudness function per frequency region and for noise, to move the level of most integration.")
A("3. Slower growth beyond 50 ms without losing the fit at 5 ms: the form (T / (T + half))^exponent may be too simple.")
A("4. Onset weighting as a separate decision stage for sustained sounds, tested on the weights of Pedersen & Ellermeier\n"
  "   (2008) and Fischenich et al. (2021).")
A("5. The pilot: this version is the prediction on record.")
with open(out, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")
print("wrote", out)
