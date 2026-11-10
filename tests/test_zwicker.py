# SPDX-License-Identifier: Apache-2.0
"""ISO 532-1 through MoSQITo: the unit, the level path, and the gain solver."""
import contextlib
import io
import os

import numpy as np
import pytest

from listener import zwicker
from listener.conformance import reference_tones as ref


def test_one_sone():
    n = zwicker.Zwicker(ref.tone(40.0, 1.0)).curve(1.0).n
    assert abs(float(np.median(n[200:400])) - 1.0) < 0.1


def test_level_path_equals_mosqito():
    """A level change as an offset on the third-octave levels gives what MoSQITo gives on the scaled signal.

    The signal ends in silence in both. MoSQITo 1.2.1's nonlinear-decay stage reads the last frame as the state before
    the first (index -1), so without that silence the first frames of N(t) depend on how the signal ends.
    """
    with contextlib.redirect_stdout(io.StringIO()):
        from mosqito.sq_metrics import loudness_zwtv
    x = ref.tone(60.0, 0.4) + 0.5 * ref.narrow_band_noise(55.0, 200.0, 4000.0, 0.4, seed=3)[: int(0.4 * 48000)]
    padded = np.concatenate([x, np.zeros(int(zwicker.TAIL_S * 48000))])
    with contextlib.redirect_stdout(io.StringIO()):
        direct = loudness_zwtv(padded * 10 ** (6 / 20), 48000, "free")[0]
    ours = zwicker.Zwicker(x).curve(1.0, 6.0).n
    assert np.abs(ours[: len(direct)] - direct[: len(ours)]).max() < 1e-3


def test_phon_and_sone():
    for p in (20.0, 40.0, 63.0, 90.0):
        assert abs(zwicker.sone_to_phon(zwicker.phon_to_sone(p)) - p) < 0.05


def test_gain_solver_on_a_tone():
    model = zwicker.Zwicker(ref.tone(60.0, 0.5))
    start = float(zwicker.sone_to_phon(model.curve(1.0).n.max()))
    res = model.gain_for_level(1.0, start + 10.0)
    assert res["converged"] and abs(res["gainDb"] - 10.0) < 0.6     # at 1 kHz a phon is a dB
    low = zwicker.Zwicker(ref.tone(90.0, 0.5, freq=63.0))
    s = float(zwicker.sone_to_phon(low.curve(1.0).n.max()))
    res = low.gain_for_level(1.0, s + 10.0)
    assert res["converged"] and res["gainDb"] < 8.0                 # at 63 Hz and 90 dB SPL ten phon cost about 7 dB


def test_sharpness_reference():
    c = zwicker.Zwicker(ref.narrow_band_noise(60.0, seconds=2.0)).curve(1.0, specific=True)
    s = zwicker.sharpness_din(c)
    assert abs(float(np.median(s[250: c.frames_signal])) - 1.0) < 0.05


@pytest.mark.skipif(not os.environ.get("LISTENER_ISO532_1"), reason="set LISTENER_ISO532_1 to the folder with Annex B.4 and B.5")
def test_iso532_1_annex_b():
    from listener.conformance import iso532
    cases = iso532.cases(os.environ["LISTENER_ISO532_1"])
    assert len(cases) >= 20
    assert all(c["pass"] for c in cases), [c["case"] for c in cases if not c["pass"]]
