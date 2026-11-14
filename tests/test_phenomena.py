# SPDX-License-Identifier: Apache-2.0
"""The benchmark's arithmetic on the cases where the answer is known by construction."""
import numpy as np

from listener.phenomena import bench


def test_energy_window_gives_ten_log_of_the_duration_ratio():
    a, b = bench.tone_burst(60.0, 0.200), bench.tone_burst(60.0, 0.005)
    la, lb = bench._linear(a), bench._linear(b)
    assert abs((la["momentaryMax"] - lb["momentaryMax"]) - 10 * np.log10(200 / 5)) < 0.4
    assert abs(la["peak"] - lb["peak"]) < 0.3      # the peak sees no duration


def test_time_reversal_is_invisible_to_energy_measures():
    x = bench.level_ramp_tone(60.0, 75.0)
    la, lb = bench._linear(x), bench._linear(x[::-1].copy())
    for key in ("peak", "rms", "momentaryMax"):
        assert abs(la[key] - lb[key]) < 0.1


def test_verdicts():
    p = {"kind": "value", "published": (18.0, 19.0)}
    assert bench._verdict(p, 18.4) == "agrees" and bench._verdict(p, 16.0) == "near" and bench._verdict(p, 9.0) == "off"
    s = {"kind": "sign", "sign": 1}
    assert bench._verdict(s, 0.1) == "no effect" and bench._verdict(s, -2.0) == "opposite" and bench._verdict(s, 2.0) == "agrees"


def _erd_ms(x, spl=60.0):
    """Equivalent rectangular duration: the sound's energy over the power of the steady tone at its stated level."""
    return 1000.0 * (x ** 2).sum() / bench.SR / bench._amp(spl) ** 2


def test_the_papers_tones_have_the_durations_the_papers_state():
    assert abs(_erd_ms(bench.erd_tone(60.0, 0.005)) - 5.0) < 0.1          # Florentine et al.: rise and fall alone
    assert abs(_erd_ms(bench.erd_tone(60.0, 0.200)) - 200.0) < 0.5
    assert abs(_erd_ms(bench.linear_gated_tone(60.0, 0.002)) - (2.0 - 0.67)) < 0.05   # Buus et al. 1997: 0.67 ms under nominal
    assert abs(_erd_ms(bench.linear_gated_tone(60.0, 0.250)) - (250.0 - 0.67)) < 0.5


def test_the_impact_envelopes_are_time_reverses_with_the_peak_early():
    fs, sf = bench.beta_envelope(-3.0), bench.beta_envelope(3.0)
    assert np.allclose(fs, sf[::-1], atol=1e-9)
    assert fs.argmax() < 0.05 * len(fs) and abs(fs.max() - 1.0) < 1e-12
    wide = bench.beta_envelope(-1.0)
    assert (wide ** 2).sum() > (fs ** 2).sum() and wide.argmax() > fs.argmax()      # as the paper says of |pt| = 1
    sym = bench.beta_envelope(0.0)
    assert np.allclose(sym, sym[::-1], atol=1e-9)


def test_octave_bands_have_their_level_and_their_place():
    x = bench.octave_band(125.0, 75.0)
    assert abs(20 * np.log10(np.sqrt((x ** 2).mean()) / bench.P0) - 75.0) < 0.3
    spec = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / bench.SR)
    assert spec[(f > 125 / 2 ** 0.5) & (f < 125 * 2 ** 0.5)].sum() / spec.sum() > 0.9


def test_a_row_that_names_the_short_sounds_level_reports_a_positive_integration():
    rows = {r["id"]: r for r in bench.phenomena()}
    p = rows["integration-tone-moderate"]
    assert p["negate"] and len(p["a"]) < len(p["b"])           # A is the 5 ms tone held at its level
    la, lb = bench._linear(p["a"]), bench._linear(p["b"])
    assert abs(-(la["momentaryMax"] - lb["momentaryMax"]) - 10 * np.log10(200 / 5)) < 0.4
    assert len(bench._hash(p)) == 16 and bench._hash(p) == bench._hash(rows["integration-tone-moderate"])
