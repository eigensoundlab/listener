# SPDX-License-Identifier: Apache-2.0
import numpy as np

from listener.calibration import Level, from_full_scale_sine, parse_levels


def test_reference_tone_and_full_scale_sine():
    lv = Level(80.0, -23.0)
    assert abs(lv.full_scale_sine_spl - 99.99) < 0.01          # 80 + 23 - 3.01
    assert abs(lv.pa_per_fs - 2.0 * np.sqrt(2)) < 0.01         # 100 dB SPL is 2 Pa RMS
    assert abs(from_full_scale_sine(100.0).ref_spl - 80.01) < 0.01


def test_levels_are_written_out():
    levels = parse_levels("70,80")
    assert [lv.id for lv in levels] == ["spl70", "spl80"]
    d = levels[0].describe()
    assert d["refLufs"] == -23.0 and "plays at 70 dB SPL" in d["text"]
