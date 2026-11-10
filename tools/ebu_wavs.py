# SPDX-License-Identifier: Apache-2.0
"""Write the synthesised EBU Tech 3341/3342 cases as WAV files, with what a meter must read, for other implementations.

usage: python tools/ebu_wavs.py <folder>      (then, for Playhead: playhead analyze <folder> --profile fast --out-dir <docs>)
Writes expected.json: file -> {measure: [expected, low tolerance, high tolerance]} with Playhead's names of the measures.
"""
import json
import os
import sys

import numpy as np
import soundfile as sf

from listener.conformance import ebu

SR = 48000
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
exp = {}


def put(name, x, **checks):
    sf.write(os.path.join(out, name + ".wav"), x, SR, subtype="PCM_24")
    exp[name + ".wav"] = checks


put("3341-01", ebu.tone(-23, 20, SR), integrated=[-23, -.1, .1], momentaryMax=[-23, -.1, .1], shortTermMax=[-23, -.1, .1])
put("3341-02", ebu.tone(-33, 20, SR), integrated=[-33, -.1, .1], momentaryMax=[-33, -.1, .1], shortTermMax=[-33, -.1, .1])
put("3341-03", ebu.sequence([(-36, 10), (-23, 60), (-36, 10)], SR), integrated=[-23, -.1, .1])
put("3341-04", ebu.sequence([(-72, 10), (-36, 10), (-23, 60), (-36, 10), (-72, 10)], SR), integrated=[-23, -.1, .1])
put("3341-05", ebu.sequence([(-26, 20), (-20, 20.1), (-26, 20)], SR), integrated=[-23, -.1, .1])
put("3341-09", ebu.sequence([(-20, 1.34), (-30, 1.66)] * 5, SR), shortTermMax=[-23, -.1, .1])
put("3341-12", ebu.sequence([(-20, 0.18), (-30, 0.22)] * 25, SR), momentaryMax=[-23, -.1, .1])
for i in (0, 7, 19):
    put(f"3341-10-{i:02d}", ebu.sequence([(None, i * 0.15), (-23, 3), (None, 1)], SR), shortTermMax=[-23, -.1, .1])
    put(f"3341-13-{i:02d}", ebu.sequence([(None, i * 0.02), (-23, 0.4), (None, 1)], SR), momentaryMax=[-23, -.1, .1])
    put(f"3341-14-{i:02d}", ebu.sequence([(None, i * 0.02), (-38 + i, 0.4), (None, 0.4 - i * 0.02)], SR),
        momentaryMax=[-38 + i, -.1, .1])
n = np.arange(int(0.5 * SR))
fade = int(0.01 * SR)
for case, div, amp, ph, e in ((15, 4, 0.5, 0.0, -6.0), (16, 4, 0.5, 45.0, -6.0), (17, 6, 0.5, 60.0, -6.0), (18, 8, 0.5, 67.5, -6.0)):
    y = amp * np.sin(2 * np.pi * n / div + np.deg2rad(ph))
    y[:fade] *= np.linspace(0, 1, fade)
    y[-fade:] *= np.linspace(1, 0, fade)
    put(f"3341-{case}", np.repeat(y[:, None], 2, axis=1), truePeak=[e, -.4, .2])
json.dump(exp, open(os.path.join(out, "expected.json"), "w"), indent=1)
print(len(exp), "files")
