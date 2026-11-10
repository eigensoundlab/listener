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
