# SPDX-License-Identifier: Apache-2.0
"""`listener phenomena`: every measure against published facts about the loudness of short and changing sounds.

No listener data for sound effects exist yet. What does exist is a body of results on tones and noises that any
model of event loudness has to reproduce first. Each phenomenon here is a pair of sounds A and B and what listeners
did: the level difference at which B sounds as loud as A (or only its sign, where that is all the literature gives).
Every measure answers the same question: by how many dB would you raise B to make it as loud as A?

Use: (1) a regression suite for any new model, including the event-level model this project will fit; (2) a statement
of what the standard measures already get wrong before any sound effect is involved; (3) for the contrasts nobody has
measured (dry against wet, boom against click), each measure's prediction on record before the listening test.

The published numbers are those checked in the project's research notes (perception_and_measures.md). The stimuli are
rebuilt from the papers' descriptions as far as the notes give them; `reconstruction` says what was assumed. The
benchmark constrains a model; it does not validate one. Validation is listener data on sound effects, held out.
"""
from __future__ import annotations

import datetime

import numpy as np

from .. import __version__, bs1770, ecma, zwicker
from ..model import literature
from ..calibration import P0
from ..measure import implementations

SR = 48000
RNG_SEED = 20261110


# ------------------------------------------------------------------ stimuli (sound pressure in Pa, 48 kHz)

def _amp(spl: float) -> float:
    return P0 * 10 ** (spl / 20)


def _ramp(x: np.ndarray, ms: float) -> np.ndarray:
    n = max(1, int(round(ms * 1e-3 * SR)))
    w = 0.5 - 0.5 * np.cos(np.pi * np.arange(n) / n)
    x = x.copy()
    x[:n] *= w
    x[-n:] *= w[::-1]
    return x


def tone_burst(spl: float, seconds: float, freq: float = 1000.0, ramp_ms: float = 1.0) -> np.ndarray:
    """A tone whose plateau has this level; `seconds` is its duration between the half-amplitude points."""
    n = int(round((seconds + ramp_ms * 1e-3) * SR))
    return _ramp(np.sqrt(2) * _amp(spl) * np.sin(2 * np.pi * freq * np.arange(n) / SR), ramp_ms)


def noise(seconds: float, lo: float = 20.0, hi: float = 20000.0, pink: bool = False, seed: int = RNG_SEED) -> np.ndarray:
    """Band-limited noise with unit RMS."""
    n = int(round(seconds * SR))
    spec = np.fft.rfft(np.random.default_rng(seed).standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec[(f < lo) | (f > hi)] = 0
    if pink:
        spec[1:] /= np.sqrt(f[1:])
    x = np.fft.irfft(spec, n)
    return x / np.sqrt((x ** 2).mean())


def noise_burst(spl: float, seconds: float, ramp_ms: float = 1.0, **kw) -> np.ndarray:
    return _ramp(_amp(spl) * noise(seconds + ramp_ms * 1e-3, **kw), ramp_ms)


def level_ramp_tone(start_spl: float, end_spl: float, seconds: float = 2.0, freq: float = 1000.0) -> np.ndarray:
    n = int(round(seconds * SR))
    level = np.linspace(start_spl, end_spl, n)
    return _ramp(np.sqrt(2) * P0 * 10 ** (level / 20) * np.sin(2 * np.pi * freq * np.arange(n) / SR), 10.0)


def decaying(carrier: np.ndarray, peak_spl: float, attack_ms: float, drop_db: float) -> np.ndarray:
    """Fast attack, then an exponential decay that has fallen by drop_db at the end."""
    n = len(carrier)
    a = max(1, int(round(attack_ms * 1e-3 * SR)))
    env = np.ones(n)
    env[:a] = np.linspace(0, 1, a)
    env[a:] = 10 ** (-drop_db * np.arange(n - a) / (n - a) / 20)
    x = carrier * env
    return x / np.abs(x).max() * np.sqrt(2) * _amp(peak_spl)


def gap(seconds: float) -> np.ndarray:
    return np.zeros(int(round(seconds * SR)))


def train(burst: np.ndarray, period_s: float, count: int) -> np.ndarray:
    out = np.zeros(int(round(period_s * SR)) * (count - 1) + len(burst))
    for i in range(count):
        a = int(round(i * period_s * SR))
        out[a:a + len(burst)] += burst
    return out


# ------------------------------------------------------------------ measures: "raise B by how much to match A?"

LINEAR = ("peak", "rms", "integrated", "momentaryMax", "shortTermMax")
LITERATURE_FITTED = ["integration-tone-moderate", "integration-tone-high", "integration-noise-moderate", "integration-noise-high",
                     "rise-fall-asymmetry", "repetition-slow", "low-frequency-band"]
MODEL = ("iso532_1.max", "iso532_1.n5")


def _linear(x: np.ndarray) -> dict:
    """Level-free measures of a pressure signal (Pa read as full-scale units: only differences are used)."""
    x2 = x[:, None]
    values, _ = bs1770.measure_span(x2, bs1770.k_weight(x2, SR), SR, 0.0, len(x) / SR)
    return values


def _secant(level_fn, target: float, tol: float = 0.05, max_iter: int = 8) -> tuple[float, bool]:
    g0, l0 = 0.0, level_fn(0.0)
    if abs(l0 - target) < tol:
        return 0.0, True
    g1 = target - l0
    for _ in range(max_iter):
        l1 = level_fn(g1)
        if abs(l1 - target) < tol or g1 == g0:
            return g1, True
        slope = min(max((l1 - l0) / (g1 - g0), 0.2), 5.0)
        g0, l0, g1 = g1, l1, g1 + (target - l1) / slope
    return g1, abs(level_fn(g1) - target) < 4 * tol


def predictions(a: np.ndarray, b: np.ndarray, ecma_python: str | None, ecma_known: float | None = None) -> dict:
    out = {}
    la, lb = _linear(a), _linear(b)
    for key in LINEAR:
        out[key] = round(la[key] - lb[key], 2)
    za, zb = zwicker.Zwicker(a), zwicker.Zwicker(b)
    na = za.curve(1.0).n
    for key, stat in (("iso532_1.max", lambda n, m: n.max()),
                      ("iso532_1.n5", lambda n, m: np.percentile(n[: m.frames_signal + int(zwicker.LAG_S / zwicker.FRAME_S)], 95))):
        target = float(zwicker.sone_to_phon(stat(na, za)))
        g, ok = _secant(lambda gain: float(zwicker.sone_to_phon(stat(zb.curve(1.0, gain).n, zb))), target)
        out[key] = round(g, 2) if ok else None
    lp = literature.FITTED
    out["literature.L0"] = round(literature.matching_gain(literature.track(a, lp.shelf_db), literature.track(b, lp.shelf_db), lp), 2)
    if ecma_known is not None:
        out["ecma418_2.max"] = ecma_known
    elif ecma_python:
        def emax(sig, gain=0.0):
            r = ecma.run([sig], 10 ** (gain / 20), ecma_python, roughness=False)
            sel = (r["time"] >= 0) & (r["time"] <= len(sig) / SR + 0.1)
            return 40.0 + 10.0 * np.log2(max(float(r["loudness"][sel].max()), 1e-6))  # loudness level, doubling per 10
        try:
            target = emax(a)
            g, ok = _secant(lambda gain: emax(b, gain), target, tol=0.1, max_iter=6)
            out["ecma418_2.max"] = round(g, 2) if ok else None
        except Exception:
            out["ecma418_2.max"] = None
    return out


# ------------------------------------------------------------------ the phenomena

def phenomena() -> list[dict]:
    P = []
    carrier_250 = np.sin(2 * np.pi * 1000 * np.arange(int(0.25 * SR)) / SR)
    noise_250 = noise(0.25, seed=RNG_SEED + 5)
    impact = decaying(noise(0.3, 100, 8000, seed=RNG_SEED + 7), 80.0, 1.0, 60.0)

    P.append(dict(
        id="integration-tone-moderate", kind="value",
        title="Temporal integration, 1 kHz tone, moderate level",
        a=tone_burst(56.0, 0.200), b=tone_burst(56.0, 0.005),
        published=(18.0, 19.0), unit="dB the 5 ms tone must be raised to match the 200 ms tone",
        source="Florentine, Buus & Poulsen (1996), JASA 99(3):1633-1644; 6 listeners",
        evidence="established", reconstruction="both tones at 56 dB SPL before matching; 1 ms raised-cosine ramps"))
    P.append(dict(
        id="integration-tone-high", kind="value",
        title="Temporal integration, 1 kHz tone, high level",
        a=tone_burst(100.0, 0.200), b=tone_burst(100.0, 0.005),
        published=(9.0, 11.0), unit="dB the 5 ms tone must be raised",
        source="Florentine, Buus & Poulsen (1996): about 10 dB near 100 dB SPL",
        evidence="established", reconstruction="both tones at 100 dB SPL; 'about 10 dB' taken as 9 to 11"))
    P.append(dict(
        id="integration-noise-moderate", kind="value",
        title="Temporal integration, broadband noise, moderate level",
        a=noise_burst(76.0, 0.200, seed=RNG_SEED + 1), b=noise_burst(76.0, 0.005, seed=RNG_SEED + 2),
        published=(18.0, 19.0), unit="dB the 5 ms noise must be raised",
        source="Florentine, Buus & Poulsen (1996): 18-19 dB near 76 dB SPL for noise",
        evidence="established", reconstruction="noise 20 Hz to 20 kHz at 76 dB SPL; 1 ms ramps"))
    P.append(dict(
        id="integration-noise-high", kind="value",
        title="Temporal integration, broadband noise, high level",
        a=noise_burst(100.0, 0.200, seed=RNG_SEED + 1), b=noise_burst(100.0, 0.005, seed=RNG_SEED + 2),
        published=(12.0, 14.0), unit="dB the 5 ms noise must be raised",
        source="Florentine, Buus & Poulsen (1996): about 13 dB near 100 dB SPL for noise",
        evidence="established", reconstruction="noise at 100 dB SPL; 'about 13 dB' taken as 12 to 14"))
    rising = level_ramp_tone(60.0, 75.0)
    P.append(dict(
        id="rise-fall-asymmetry", kind="value",
        title="A rising tone is louder than the same tone falling",
        a=rising, b=rising[::-1].copy(),
        published=(3.1, 5.3), unit="dB the falling tone must be raised to match the rising one",
        source="Ponsot, Susini & Meunier (2015), Atten. Percept. Psychophys. 77(3):907-920; 10 to 16 listeners, two methods",
        evidence="established", reconstruction="1 kHz, 2 s, 60 to 75 dB SPL linear in dB (the paper used 15 dB ramps within 45-90 dB SPL)"))
    for name, carrier in (("tone", carrier_250), ("noise", noise_250)):
        fs = decaying(carrier, 75.0, 2.0, 40.0)
        P.append(dict(
            id=f"decay-suppression-{name}", kind="sign", sign=-1,
            title=f"An impact-like envelope is softer than its time reverse ({name})",
            a=fs, b=fs[::-1].copy(),
            published=(-3.0, -1.0), unit="dB the reversed (slow attack, fast decay) sound must be lowered to match the impact-like one",
            source="Stecker & Hafter (2000), JASA 107(6):3358-3368; 250 ms envelopes of equal energy; about 1-3 dB for one listener",
            evidence="single study; the sign is the finding, the size is weak",
            reconstruction="2 ms attack, exponential decay of 40 dB over 250 ms; the paper's time constants were not available"))
    burst = decaying(noise(0.05, seed=RNG_SEED + 3), 80.0, 1.0, 40.0)
    P.append(dict(
        id="repetition-slow", kind="value",
        title="A slow train of impulses is as loud as one impulse",
        a=burst, b=train(burst, 4.0, 3),
        published=(-1.0, 1.0), unit="dB the train must be raised to match the single impulse (none)",
        source="Ogura, Suzuki & Sone (1991), J. Acoust. Soc. Jpn (E) 12(1):1-11: no change up to 0.2-0.7 impulses a second",
        evidence="single study", reconstruction="noise impulse of 50 ms, three of them 4 s apart (0.25 a second); 'as loud' taken as within 1 dB"))
    P.append(dict(
        id="repetition-fast", kind="sign", sign=-1,
        title="A fast train of impulses is louder than one impulse",
        a=burst, b=train(burst, 0.2, 10),
        published=None, unit="dB the train must be lowered to match the single impulse",
        source="Ogura, Suzuki & Sone (1991): above the critical rate loudness grows with rate",
        evidence="single study; sign only", reconstruction="the same impulse, ten of them 0.2 s apart (5 a second)"))
    P.append(dict(
        id="low-frequency-band", kind="value",
        title="A 63 Hz octave band of noise against a 1 kHz band",
        a=_ramp(_amp(75.0) * noise(4.0, 707.0, 1414.0, pink=True, seed=RNG_SEED + 4), 20.0),
        b=_ramp(_amp(75.0) * noise(4.0, 44.5, 89.0, pink=True, seed=RNG_SEED + 4), 20.0),
        published=(9.0, 11.0), unit="dB the 63 Hz band must be raised to match the 1 kHz band",
        source="Fenton & Lee (2017), AES 143rd Convention: listeners gave 9.98 dB where BS.1770 gives 2.73; 13 listeners, loudspeakers",
        evidence="single study", reconstruction="octave bands of pink noise, both at 75 dB SPL; 9.98 dB taken as 9 to 11"))
    base = _amp(65.0) * noise(1.0, seed=RNG_SEED + 6)
    early, late = base.copy(), base.copy()
    early[: int(0.1 * SR)] *= 2.0
    late[int(0.5 * SR): int(0.6 * SR)] *= 2.0
    P.append(dict(
        id="primacy", kind="sign", sign=1,
        title="A louder beginning counts for more than a louder middle",
        a=_ramp(early, 2.0), b=_ramp(late, 2.0),
        published=None, unit="dB the sound with the louder middle must be raised to match the one with the louder beginning",
        source="Fischenich, Hots, Verhey, Guldan & Oberfeld (2021), PLoS ONE 16(12):e0261001: onset weight 4-5 times the later weight, time constant 200-300 ms",
        evidence="established; sign only", reconstruction="1 s noise at 65 dB SPL, 6 dB more in the first 100 ms or from 500 to 600 ms"))

    # contrasts nobody has measured: each measure's prediction, on record before the listening test
    tail = _amp(80.0) * 10 ** (-12 / 20) * noise(2.0, 100, 8000, seed=RNG_SEED + 8) * 10 ** (-60 * np.arange(int(2.0 * SR)) / (2.0 * SR) / 20)
    wet = np.concatenate([impact, np.zeros(len(tail) - len(impact))]) + np.concatenate([np.zeros(int(0.01 * SR)), tail[:-int(0.01 * SR)]])
    P.append(dict(
        id="open-dry-wet", kind="open", title="The same impact dry and with a 2 s reverberant tail",
        a=impact, b=wet, published=None, unit="dB the wet version would be raised (negative: lowered) to match the dry one",
        source="no listener data found (perception_and_measures.md, section 3)", evidence="open question",
        reconstruction="noise impact of 0.3 s; tail 12 dB under its peak, decaying 60 dB in 2 s"))
    for spl in (60.0, 80.0):
        click = _ramp(_amp(spl) * noise(0.03, 2000, 6000, seed=RNG_SEED + 9), 2.0)
        boom_n = int(1.2 * SR)
        boom = _amp(spl) * noise(1.2, 30, 150, seed=RNG_SEED + 10) * np.exp(-np.arange(boom_n) / (0.25 * SR))
        boom[: int(0.005 * SR)] *= np.linspace(0, 1, int(0.005 * SR))
        P.append(dict(
            id=f"open-boom-click-{spl:g}", kind="open", title=f"A 30-150 Hz boom against a 2-6 kHz click, around {spl:g} dB SPL",
            a=click, b=boom, published=None, unit="dB the boom would be raised to match the click",
            source="no listener data found (perception_and_measures.md, section 4)", evidence="open question",
            reconstruction="click 30 ms; boom 1.2 s with a 250 ms decay; both built from noise of the stated level"))
    return P


def _verdict(p: dict, value: float | None) -> str:
    if value is None:
        return "no value"
    if p["kind"] == "open":
        return "prediction"
    if p["kind"] == "sign":
        if abs(value) < 0.5:
            return "no effect"
        return "agrees" if np.sign(value) == p["sign"] else "opposite"
    lo, hi = p["published"]
    miss = max(lo - value, value - hi, 0.0)
    return "agrees" if miss <= 1.0 else ("near" if miss <= 3.0 else "off")


def _miss(p: dict, value: float | None):
    if value is None or p["kind"] != "value":
        return None
    lo, hi = p["published"]
    return round(value - hi if value > hi else (value - lo if value < lo else 0.0), 2)


def run(levels=None, ecma_python: str | None = None, ecma_from: dict | None = None) -> dict:
    """`ecma_from`: an earlier listener-phenomena document of the same version whose ECMA-418-2 values are kept
    (they take most of the run's time and do not depend on anything else here)."""
    rows = []
    known = {}
    if ecma_from and ecma_from.get("generator", {}).get("version") == __version__:
        known = {r["id"]: r["predictions"].get("ecma418_2.max") for r in ecma_from["phenomena"]}
    for p in phenomena():
        pred = predictions(p["a"], p["b"], ecma_python, known.get(p["id"]))
        rows.append({
            "id": p["id"], "kind": p["kind"], "title": p["title"], "question": p["unit"],
            "published": list(p["published"]) if p["published"] else None,
            "expectedSign": p.get("sign"), "source": p["source"], "evidence": p["evidence"],
            "reconstruction": p["reconstruction"],
            "predictions": pred,
            "miss": {k: _miss(p, v) for k, v in pred.items()},
            "verdicts": {k: _verdict(p, v) for k, v in pred.items()},
        })
    measures = list(rows[0]["predictions"])
    tested = [r for r in rows if r["kind"] != "open"]
    score = {m: {"agrees": sum(1 for r in tested if r["verdicts"][m] == "agrees"),
                 "near": sum(1 for r in tested if r["verdicts"][m] == "near"),
                 "of": len(tested)} for m in measures}
    return {
        "format": "listener-phenomena", "version": 1,
        "generator": {"name": "listener", "version": __version__},
        "created": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "implementations": implementations(ecma_python or ("reused" if known else None)),
        **({"ecmaReusedFrom": ecma_from.get("created")} if known else {}),
        "rule": "Each value: dB by which a measure would raise sound B to make it as loud as sound A. 'agrees': within 1 dB of the published range (or the right sign, at least 0.5 dB); 'near': within 3 dB; 'off': further; 'no effect': under 0.5 dB where a sign is expected; 'opposite': the wrong sign.",
        "caution": "Stimuli are rebuilt from descriptions; the published ranges come from small panels. This constrains a model. It does not validate one for sound effects.",
        "measures": measures, "score": score,
        "literatureModel": {
            "note": "literature.L0 was set from the rows in 'fitted'; only the rows in 'heldOut' test it; 'notModelled' it is expected to fail",
            "fitted": LITERATURE_FITTED, "heldOut": [r["id"] for r in tested if r["id"] not in LITERATURE_FITTED and r["id"] != "primacy"],
            "notModelled": ["primacy"],
            "scoreHeldOut": {m: sum(1 for r in tested if r["id"] not in LITERATURE_FITTED and r["verdicts"][m] == "agrees") for m in measures},
        },
        "phenomena": rows,
    }


def report_markdown(doc: dict) -> str:
    ms = doc["measures"]
    short = {"peak": "Peak", "rms": "RMS", "integrated": "LUFS-I", "momentaryMax": "Max M", "shortTermMax": "Max S",
             "iso532_1.max": "ISO 532-1 Nmax", "iso532_1.n5": "ISO 532-1 N5", "ecma418_2.max": "ECMA-418-2 max",
             "literature.L0": "Literature model L0"}
    mark = {"agrees": "", "near": " ~", "off": " ✗", "no effect": " ✗ (none)", "opposite": " ✗ (opposite)", "prediction": "", "no value": ""}
    L = ["# Published loudness phenomena against the measures\n", doc["rule"] + "\n", doc["caution"] + "\n",
         "| Phenomenon | Listeners | " + " | ".join(short.get(m, m) for m in ms) + " |", "|---|---|" + "---|" * len(ms)]
    for r in doc["phenomena"]:
        if r["kind"] == "open":
            continue
        pub = (f"{r['published'][0]:g} to {r['published'][1]:g}" if r["published"] else "") if r["kind"] == "value" else \
              (("positive" if r["expectedSign"] > 0 else "negative") + (f" ({r['published'][0]:g} to {r['published'][1]:g})" if r["published"] else ""))
        fitted = r["id"] in doc.get("literatureModel", {}).get("fitted", [])
        L.append(f"| {r['title']}{' †' if fitted else ''} | {pub} | " + " | ".join(
            ("–" if r["predictions"][m] is None else f"{r['predictions'][m]:+.1f}") + mark[r["verdicts"][m]] for m in ms) + " |")
    L.append("| **Agrees (near)** | | " + " | ".join(f"**{doc['score'][m]['agrees']}** ({doc['score'][m]['near']}) of {doc['score'][m]['of']}" for m in ms) + " |")
    L.append("\n✗: more than 3 dB from the published range, no effect where one is expected, or the wrong sign. ~: within 3 dB.\n")
    if "literatureModel" in doc:
        L.append("†: a result the literature model was set from. For that model only the rows without † are a test, and it has no onset weighting, so the last row is expected to fail.\n")
    L.append("## Contrasts nobody has measured: the predictions on record\n")
    L.append("| Contrast | " + " | ".join(short.get(m, m) for m in ms) + " | Spread |")
    L.append("|---|" + "---|" * (len(ms) + 1))
    for r in doc["phenomena"]:
        if r["kind"] != "open":
            continue
        vals = [v for v in r["predictions"].values() if v is not None]
        L.append(f"| {r['title']} | " + " | ".join("–" if r["predictions"][m] is None else f"{r['predictions'][m]:+.1f}" for m in ms)
                 + f" | {max(vals) - min(vals):.1f} |")
    L.append("\n## Sources and what was assumed\n")
    for r in doc["phenomena"]:
        L.append(f"- **{r['title']}.** {r['question']}. {r['source']} [{r['evidence']}]. Assumed: {r['reconstruction']}.")
    return "\n".join(L) + "\n"
