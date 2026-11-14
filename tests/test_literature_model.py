# SPDX-License-Identifier: Apache-2.0
"""The literature model L0: what must hold by construction, and that its published results are reproduced."""
import json
import os

import numpy as np
import pytest

from listener.model import literature as M
from listener.phenomena import bench as B

P = M.FITTED
RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "literature-model", "fit.json")


@pytest.mark.parametrize("spl", [30.0, 60.0, 90.0])
def test_a_steady_tone_reads_its_own_level(spl):
    assert abs(M.event_level(M.track(B.tone_burst(spl, 2.0)), P) - spl) < 0.3


def test_silence_around_a_sound_changes_nothing():
    hit = B.decaying(B.noise(0.3, 100, 8000, seed=3), 80.0, 1.0, 60.0)
    padded = np.concatenate([np.zeros(48000), hit, np.zeros(96000)])
    assert abs(M.event_level(M.track(hit), P) - M.event_level(M.track(padded), P)) < 0.05


def _integration(spl, params):
    """dB the 5 ms tone lies above the equally loud 200 ms tone, the 5 ms tone held at spl."""
    return -M.matching_gain(M.track(B.erd_tone(spl, .005)), M.track(B.erd_tone(spl, .200)), params)


def test_level_dependence_comes_from_the_loudness_function():
    assert _integration(56, P) - _integration(100, P) > 4.0          # more integration at the moderate level
    flat = M.Params(beta=P.beta, t_half=P.t_half, loudness="power")
    assert abs(_integration(56, flat) - _integration(100, flat)) < 0.2  # none without the inflected function


def test_matching_gain_is_antisymmetric_enough():
    a, b = M.track(B.tone_burst(60, .2)), M.track(B.tone_burst(60, .02))
    g = M.matching_gain(a, b, P)
    raised = M.track(B.tone_burst(60 + g, .02))
    assert abs(M.event_level(raised, P) - M.event_level(a, P)) < 0.1


@pytest.mark.skipif(not os.path.isfile(RESULTS), reason="results/literature-model/fit.json not present")
def test_the_stored_fit_is_reproduced():
    doc = json.load(open(RESULTS))
    assert abs(doc["parameters"]["beta"] - P.beta) < 1e-6 and abs(doc["parameters"]["t_half"] - P.t_half) < 1e-6
    rows = {r["id"]: r for r in B.phenomena()}
    assert abs(_integration(56, P) - doc["fit"]["F1"]["predicted"]) < 0.06
    ramp = rows["rise-fall-asymmetry"]
    f6 = M.matching_gain(M.track(ramp["a"]), M.track(ramp["b"]), P)
    assert abs(f6 - doc["fit"]["F6"]["predicted"]) < 0.06
