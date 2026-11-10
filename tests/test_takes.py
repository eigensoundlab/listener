# SPDX-License-Identifier: Apache-2.0
"""`listener takes`: takes are cut sample for sample, checked, and listed in a manifest."""
import csv
import json

import numpy as np
import soundfile as sf

from listener import takes

SR = 48000
HEAD = ["name", "file", "start", "length", "fade_in", "fade_out", "gain_db", "rate", "reversed", "take_fx", "position"]


def _session(tmp_path, rows):
    rng = np.random.default_rng(7)
    raw = 1e-4 * rng.standard_normal(6 * SR)                          # room tone, about -80 dBFS
    t = np.arange(int(0.5 * SR)) / SR
    hit = np.sin(2 * np.pi * 700 * t) * np.exp(-t / 0.04)
    hit[: int(0.003 * SR)] *= np.linspace(0, 1, int(0.003 * SR)) ** 2  # a 3 ms attack
    raw[1 * SR + 480: 1 * SR + 480 + len(hit)] += 0.4 * hit            # the hit starts 10 ms after 1.0 s
    raw[3 * SR: 3 * SR + len(hit)] += 1.6 * hit                        # too hot: clips
    raw = np.clip(raw, -1, 1 - 2 ** -23)
    (tmp_path / "raw").mkdir()
    sf.write(tmp_path / "raw" / "rec-001.wav", raw, SR, subtype="PCM_24")
    with open(tmp_path / "takes.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(HEAD)
        w.writerows(rows)
    return raw


def test_cut_is_sample_exact_and_checked(tmp_path):
    raw = _session(tmp_path, [
        ["knock_medium_01", "raw/rec-001.wav", 1.0, 0.45, 0, 0.02, 0, 1, 0, 0, 10],
        ["knock_hard_01", "raw/rec-001.wav", 2.99, 0.5, 0, 0.02, 0, 1, 0, 0, 12],
        ["knock_medium_02", "raw/rec-001.wav", 1.02, 0.1, 0, 0, 0, 1, 0, 0, 14],     # cut into the attack and the tail
        ["roomtone_-_01", "raw/rec-001.wav", 4.5, 1.0, 0, 0, 0, 1, 0, 0, 0],
        ["knock_soft_01", "raw/rec-001.wav", 1.0, 0.4, 0, 0, -3.0, 1, 0, 0, 16],    # a gain in REAPER: not a raw take
    ])
    (tmp_path / "session.json").write_text(json.dumps({"microphone": "test", "licence": "CC0-1.0"}))
    doc = takes.run(str(tmp_path / "takes.csv"), str(tmp_path / "out"), str(tmp_path / "session.json"))
    assert doc["format"] == "listener-recordings" and doc["session"]["licence"] == "CC0-1.0"
    assert [r["name"] for r in doc["refused"]] == ["knock_soft_01"] and "gain" in doc["refused"][0]["why"]
    by = {f["file"]: f for f in doc["files"]}

    out, sr = sf.read(tmp_path / "out" / "knock_medium_01.wav", dtype="int32")
    src, _ = sf.read(tmp_path / "raw" / "rec-001.wav", dtype="int32", start=SR, frames=int(0.45 * SR))
    keep = len(out) - int(0.02 * SR)
    assert sf.info(tmp_path / "out" / "knock_medium_01.wav").subtype == "PCM_24" and sr == SR
    assert np.array_equal(out[:keep], src[:keep])                        # the raw samples, bit for bit
    assert np.abs(out[keep:]).sum() < np.abs(src[keep:]).sum()            # and the item's fade over the last 20 ms

    f = by["knock_medium_01.wav"]
    assert f["id"] == "knock" and f["strength"] == "medium" and f["take"] == 1 and f["flags"] == []
    assert abs(f["levels"]["peak"] - 20 * np.log10(0.4)) < 1.0 and f["levels"]["peakAboveRoomTone"] > 60
    assert "clipped" in by["knock_hard_01.wav"]["flags"]
    assert {"starts-loud", "ends-loud"} <= set(by["knock_medium_02.wav"]["flags"])
    assert doc["roomTone"]["file"] == "roomtone_-_01.wav" and -85 < doc["roomTone"]["rms"] < -75
    assert json.loads((tmp_path / "out" / "manifest.json").read_text())["files"][0]["sha256"]
