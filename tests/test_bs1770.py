# SPDX-License-Identifier: Apache-2.0
"""BS.1770 / EBU measures against values known by construction."""
import numpy as np
import pytest

from listener import bs1770
from listener.conformance import ebu

SR = 48000


def test_ebu_cases_synthesised_from_tech_3341_and_3342():
    failed = [(c["suite"], c["case"], c["measured"]) for c in ebu.cases(SR) if not c["pass"]]
    assert not failed, failed


def test_other_sample_rate():
    x = ebu.tone(-23.0, 5, 44100)
    assert abs(bs1770.integrated(x, 44100) + 23.0) < 0.1


@pytest.mark.parametrize("ms,expected", [(100, -6.02), (200, -3.01), (50, -9.03)])
def test_short_burst_reads_as_a_window_with_silence(ms, expected):
    steady = ebu.tone(-20.0, 2, SR)
    burst = ebu.tone(-20.0, ms / 1000, SR)
    ref = bs1770.window_loudness(bs1770.k_weight(steady, SR), SR, 0.4).max()
    got = bs1770.window_loudness(bs1770.k_weight(burst, SR), SR, 0.4).max()
    assert abs((got - ref) - expected) < 0.15


def test_mono_counts_once():
    stereo = ebu.tone(-23.0, 3, SR)
    mono = stereo[:, :1]
    assert abs(bs1770.integrated(stereo, SR) - bs1770.integrated(mono, SR) - 3.01) < 0.02


def test_span_rules_are_reported():
    x = np.vstack([ebu.silence(0.5, SR), ebu.tone(-20.0, 0.1, SR), ebu.silence(0.5, SR)])
    values, notes = bs1770.measure_span(x, bs1770.k_weight(x, SR), SR, 0.5, 0.6)
    assert "integrated-single-block" in notes and "momentary-padded" in notes
    assert abs(values["integrated"] + 20.0) < 0.2          # the span's own mean
    assert abs(values["momentaryMax"] + 26.0) < 0.2        # 0.1 s in a 0.4 s window
    assert abs(values["peak"] + 20.0) < 0.05


def test_integrated_agrees_with_pyloudnorm_on_long_signals_and_counts_complete_blocks_only():
    import pyloudnorm as pyln
    rng = np.random.default_rng(4)
    env = np.repeat(10 ** (rng.uniform(-30, -6, 40) / 20), SR // 4)       # 10 s of noise in steps of level
    x = (rng.standard_normal(len(env)) * env)[:, None] * 0.3
    assert abs(bs1770.integrated(x, SR) - pyln.Meter(SR).integrated_loudness(x[:, 0])) < 0.05
    # 0.478 s: one complete block. A decaying hit must read what its only block reads.
    t = np.arange(int(0.478 * SR)) / SR
    hit = (np.sin(2 * np.pi * 900 * t) * np.exp(-t / 0.3))[:, None] * 0.5
    ky = bs1770.k_weight(hit, SR)
    one_block = bs1770.window_loudness(ky[: int(0.4 * SR)], SR, 0.4)[0]
    assert abs(bs1770.integrated(hit, SR) - one_block) < 0.01
    assert pyln.Meter(SR).integrated_loudness(hit[:, 0]) < one_block - 0.5    # pyloudnorm 0.2.0 adds a partial block
