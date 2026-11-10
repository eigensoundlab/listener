# SPDX-License-Identifier: Apache-2.0
"""Reading audio. Samples are float64 in [-1, 1], shape (frames, channels)."""
from __future__ import annotations

import os
import shutil
import subprocess
from math import gcd

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

MODEL_RATE = 48000  # ISO 532-1 and ECMA-418-2 are defined at 48 kHz


def load(path: str):
    """Return (samples, sample_rate, info). Formats libsndfile cannot read go through ffmpeg if it is on the PATH."""
    path = os.fspath(path)
    try:
        info = sf.info(path)
        x, sr = sf.read(path, dtype="float64", always_2d=True)
        meta = {"sampleRate": int(sr), "channels": int(x.shape[1]), "subtype": info.subtype, "format": info.format}
    except Exception:
        if not shutil.which("ffmpeg"):
            raise
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate,channels",
             "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout.strip().split(",")
        sr, ch = int(probe[0]), int(probe[1])
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f64le", "-acodec", "pcm_f64le", "-"],
                             capture_output=True, check=True).stdout
        x = np.frombuffer(raw, dtype="<f8").reshape(-1, ch).copy()
        meta = {"sampleRate": sr, "channels": ch, "subtype": "via-ffmpeg", "format": os.path.splitext(path)[1][1:]}
    meta["frames"] = int(x.shape[0])
    meta["duration"] = x.shape[0] / float(sr)
    return x, int(sr), meta


def to_model_rate(x: np.ndarray, sr: int) -> np.ndarray:
    """Resample to 48 kHz (polyphase), the rate the hearing models are specified at."""
    if sr == MODEL_RATE:
        return x
    g = gcd(MODEL_RATE, int(sr))
    return resample_poly(x, MODEL_RATE // g, int(sr) // g, axis=0)


def ear_signals(x: np.ndarray):
    """The signals reaching the two ears in headphone listening: a mono file is heard in both ears.

    Returns a list of 1-D arrays with identical channels merged, and for each the number of ears it feeds.
    Files with more than two channels are not ear signals; the caller reports that and uses the first two.
    """
    if x.shape[1] == 1:
        return [(x[:, 0], 2)]
    left, right = x[:, 0], x[:, 1]
    if np.array_equal(left, right):
        return [(left, 2)]
    return [(left, 1), (right, 1)]
