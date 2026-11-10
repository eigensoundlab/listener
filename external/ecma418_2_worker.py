# SPDX-License-Identifier: AGPL-3.0-only
# This file imports sottek-hearing-model (AGPL-3.0-only) and is offered under that licence. It is run as a separate
# process by listener (Apache-2.0) and shares no code with it. See external/README.md.
"""ECMA-418-2:2025 loudness, tonality and roughness of ear signals, written as JSON.

usage: ecma418_2_worker.py <signals.npz> <out.json> [--no-roughness]
  signals.npz: "p" (frames, ears) sound pressure in Pa at 48 kHz
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import numpy as np
from sottek_hearing_model import shm_loudness_ecma_from_comp, shm_roughness_ecma, shm_tonality_ecma


def main(argv):
    src, dst = argv[1], argv[2]
    rough = "--no-roughness" not in argv
    p = np.load(src)["p"]
    if p.ndim == 1:
        p = p[:, None]
    out = {"implementation": "sottek-hearing-model", "standard": "ECMA-418-2:2025", "ears": []}
    try:
        from importlib.metadata import version
        out["version"] = version("sottek-hearing-model")
    except Exception:
        pass
    for ch in range(p.shape[1]):
        sig = np.ascontiguousarray(p[:, ch])
        ton = shm_tonality_ecma(sig, 48000, axis=0, soundfield="free_frontal", wait_bar=False, out_plot=False)
        lou = shm_loudness_ecma_from_comp(ton["spec_tonal_loudness"], ton["spec_noise_loudness"],
                                          out_plot=False, binaural=False)
        ear = {
            "time": np.asarray(lou["time_out"]).ravel().tolist(),
            "loudness": np.asarray(lou["loudness_t"]).ravel().tolist(),
            "loudnessPowAvg": float(np.asarray(lou["loudness_powavg"]).ravel()[0]),
            "tonality": np.asarray(ton["tonality_t"]).ravel().tolist(),
            "tonalityAvg": float(np.asarray(ton["tonality_avg"]).ravel()[0]),
        }
        if rough:
            try:
                ro = shm_roughness_ecma(sig, 48000, axis=0, soundfield="free_frontal", wait_bar=False,
                                        out_plot=False, binaural=False)
                ear["roughnessTime"] = np.asarray(ro["time_out"]).ravel().tolist()
                ear["roughness"] = np.asarray(ro["roughness_t"]).ravel().tolist()
                ear["roughness90"] = float(np.asarray(ro["roughness90pc"]).ravel()[0])
            except Exception as exc:  # too short for the roughness blocks
                ear["roughnessError"] = str(exc)[:200]
        out["ears"].append(ear)
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh)


if __name__ == "__main__":
    main(sys.argv)
