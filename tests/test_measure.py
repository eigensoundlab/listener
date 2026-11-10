# SPDX-License-Identifier: Apache-2.0
"""`listener measure` end to end on a synthetic file with a Playhead document."""
import json

import numpy as np
import soundfile as sf

from listener import measure
from listener.calibration import parse_levels
from listener.cli import main

SR = 48000


def _file(tmp_path):
    t = np.arange(int(0.15 * SR)) / SR
    hit = 0.5 * np.sin(2 * np.pi * 800 * t) * np.exp(-t / 0.03)
    x = np.concatenate([np.zeros(int(0.2 * SR)), hit, np.zeros(int(0.6 * SR)), 0.25 * hit, np.zeros(int(0.3 * SR))])
    wav = tmp_path / "two_hits.wav"
    sf.write(wav, x, SR, subtype="PCM_24")
    doc = {"schema": "playhead-analysis", "schemaVersion": 1, "generator": {"name": "playhead", "version": "test"},
           "profile": "sfx", "assetClass": "sfx",
           "summary": {"soundStart": 0.2, "soundEnd": 1.1},
           "events": [{"start": 0.2, "end": 0.35, "decayEnd": 0.33, "peakDb": -8.0, "facture": "impulse"},
                      {"start": 0.95, "end": 1.1, "decayEnd": 1.08, "peakDb": -20.0, "facture": "impulse"}]}
    (tmp_path / "two_hits.playhead.json").write_text(json.dumps(doc))
    return wav


def test_measure_per_event_and_per_level(tmp_path):
    wav = _file(tmp_path)
    doc = measure.measure([str(wav)], parse_levels("70,80"))
    assert doc["format"] == "listener-measures" and doc["version"] == 1
    assert [lv["id"] for lv in doc["calibration"]["levels"]] == ["spl70", "spl80"]
    f = doc["files"][0]
    ids = [s["id"] for s in f["spans"]]
    assert ids == ["file", "active", "event:0", "event:1"]
    e0, e1 = f["spans"][2], f["spans"][3]
    assert e0["loudest"] and e0["class"] == "impulse"
    assert abs((e0["bs1770"]["momentaryMax"] - e1["bs1770"]["momentaryMax"]) - 12.04) < 0.3   # the second hit is half the first
    a, b = e0["byLevel"]["spl70"]["iso532_1"], e0["byLevel"]["spl80"]["iso532_1"]
    assert b["nMax"] > a["nMax"] > e1["byLevel"]["spl70"]["iso532_1"]["nMax"] > 0
    assert "integrated-single-block" in e0["notes"]
    assert "din45692" in e0["byLevel"]["spl80"]
    assert doc["implementations"]["ecma418_2"] is None and "iso532_1" in doc["domains"]


def test_without_a_document_the_output_says_so(tmp_path):
    wav = _file(tmp_path)
    (tmp_path / "two_hits.playhead.json").unlink()
    doc = measure.measure([str(wav)], parse_levels("80"))
    assert doc["files"][0]["notes"] == ["no-playhead-document"]
    assert [s["id"] for s in doc["files"][0]["spans"]] == ["file"]


def test_command_line(tmp_path):
    wav = _file(tmp_path)
    out = tmp_path / "m.json"
    assert main(["measure", str(wav), "--levels", "80", "--out", str(out)]) == 0
    assert json.loads(out.read_text())["files"][0]["path"] == "two_hits.wav"
