# SPDX-License-Identifier: Apache-2.0
"""`listener takes`: cut named takes out of raw recordings, sample for sample, and write their manifest.

Input: takes.csv, written in REAPER by "Listener - Export take list" (recording/reaper/), and a session file with
what a file cannot say about itself (room, microphone, gain, distance, licence). Output: one WAV per take, in the raw
file's own sample format, and manifest.json, "format": "listener-recordings", version 1.

A take is the recording as it was. The samples are copied, not rendered: no gain, no resampling, no dither. The one
change is a linear fade at each end when the item in REAPER had one, and the manifest says so per file. Rows with a
gain, a play rate, take FX or a reversed source are refused.

Each take is checked, and the manifest carries the findings: clipped, hot (peak above -3 dBFS), a start or an end
that is not quiet (an attack or a tail cut off), DC offset, and its level above the session's room tone.
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import json
import os
import re

import numpy as np
import soundfile as sf

from . import __version__

FORMAT = "listener-recordings"
FORMAT_VERSION = 1
NAME = re.compile(r"^([A-Za-z0-9-]+)_([A-Za-z0-9-]+)_(\d+)$")
ROOM_TONE = "roomtone"
FULL_SCALE = {"PCM_16": 2 ** 15, "PCM_24": 2 ** 23, "PCM_32": 2 ** 31}


def _db(x: float) -> float:
    return float(20 * np.log10(max(x, 1e-12)))


def read_rows(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    need = {"name", "file", "start", "length"}
    if not rows or not need <= set(rows[0]):
        raise ValueError(f"{path}: expected the columns {sorted(need)} (written by 'Listener - Export take list')")
    return rows


def refusal(row: dict) -> str | None:
    """Why a row is not a raw take, or None."""
    if not NAME.match(row["name"]):
        return "name is not id_strength_number"
    if abs(float(row.get("gain_db") or 0)) > 0.001:
        return f"item or take gain of {float(row['gain_db']):+.2f} dB"
    if abs(float(row.get("rate") or 1) - 1) > 1e-9:
        return "play rate is not 1"
    if int(float(row.get("reversed") or 0)):
        return "reversed source"
    if int(float(row.get("take_fx") or 0)):
        return "take FX"
    return None


def cut(row: dict, base: str) -> tuple[np.ndarray, int, str]:
    """The take's frames as stored (integers for PCM files), its sample rate and sample format."""
    path = row["file"] if os.path.isabs(row["file"]) else os.path.join(base, row["file"])
    info = sf.info(path)
    start = int(round(float(row["start"]) * info.samplerate))
    frames = int(round(float(row["length"]) * info.samplerate))
    if start < 0 or start + frames > info.frames:
        raise ValueError(f"{row['name']}: the take runs outside {os.path.basename(path)}")
    integer = info.subtype in FULL_SCALE
    data, sr = sf.read(path, start=start, frames=frames, dtype="int32" if integer else "float64", always_2d=True)
    if integer and info.subtype != "PCM_32":  # soundfile scales narrower integers up to 32 bits: bring them back
        data = data >> (32 - {"PCM_16": 16, "PCM_24": 24}[info.subtype])
    return data, sr, info.subtype


def apply_fades(data: np.ndarray, sr: int, fade_in: float, fade_out: float) -> np.ndarray:
    n_in, n_out = int(round(fade_in * sr)), int(round(fade_out * sr))
    if n_in <= 0 and n_out <= 0:
        return data
    gain = np.ones(len(data))
    if n_in > 0:
        gain[:n_in] = np.arange(n_in) / n_in
    if n_out > 0:
        gain[-n_out:] = np.minimum(gain[-n_out:], np.arange(n_out, 0, -1) / n_out)
    faded = data * gain[:, None]
    return np.rint(faded).astype(data.dtype) if np.issubdtype(data.dtype, np.integer) else faded


def checks(x: np.ndarray, sr: int, faded_end: bool, room_rms_db: float | None) -> tuple[dict, list[str]]:
    """Levels of a take (x in full-scale units) and what looks wrong with it."""
    mono = x.mean(axis=1)
    peak = float(np.abs(x).max())
    flags: list[str] = []
    values = {"peak": round(_db(peak), 2), "rms": round(_db(float(np.sqrt((x ** 2).mean()))), 2)}
    if values["peak"] > -0.5:  # a flat top: three or more samples in a row at the take's own maximum
        at_peak = (np.abs(x) >= peak).any(axis=1).astype(int)
        if len(x) >= 3 and np.convolve(at_peak, np.ones(3, dtype=int), "valid").max() >= 3:
            flags.append("clipped")
    if "clipped" not in flags and values["peak"] > -3.0:
        flags.append("hot")
    edge = max(1, int(0.002 * sr))
    head = _db(float(np.abs(mono[:edge]).max())) - values["peak"]
    tail = _db(float(np.abs(mono[-max(1, int(0.005 * sr)):]).max())) - values["peak"]
    values["startBelowPeak"] = round(-head, 1)
    values["endBelowPeak"] = round(-tail, 1)
    if head > -20.0:
        flags.append("starts-loud")       # within 20 dB of the peak in the first 2 ms: the attack may be cut
    if tail > -40.0 and not faded_end:
        flags.append("ends-loud")         # within 40 dB of the peak in the last 5 ms, and no fade: the tail is cut
    dc = _db(abs(float(mono.mean()))) - values["peak"]
    if dc > -40.0:
        flags.append("dc-offset")
    if room_rms_db is not None:
        values["peakAboveRoomTone"] = round(values["peak"] - room_rms_db, 1)
        if values["peakAboveRoomTone"] < 40.0:
            flags.append("near-room-tone")
    return values, flags


def run(takes_csv: str, out: str, session_path: str | None = None, base: str | None = None) -> dict:
    rows = read_rows(takes_csv)
    base = base or os.path.dirname(os.path.abspath(takes_csv))
    os.makedirs(out, exist_ok=True)
    session = {}
    if session_path:
        with open(session_path, encoding="utf-8") as fh:
            session = json.load(fh)

    cut_rows, refused = [], []
    for row in rows:
        why = refusal(row)
        if why:
            refused.append({"name": row["name"], "why": why})
            continue
        data, sr, subtype = cut(row, base)
        cut_rows.append((row, data, sr, subtype))

    room = [(_r, d, s, t) for _r, d, s, t in cut_rows if NAME.match(_r["name"]).group(1) == ROOM_TONE]
    room_db = None
    if room:
        _, d, _, t = room[0]
        scale = FULL_SCALE.get(t, 1.0)
        room_db = _db(float(np.sqrt(((d / scale) ** 2).mean())))

    files = []
    for row, data, sr, subtype in sorted(cut_rows, key=lambda c: c[0]["name"]):
        fade_in, fade_out = float(row.get("fade_in") or 0), float(row.get("fade_out") or 0)
        data = apply_fades(data, sr, fade_in, fade_out)
        scale = FULL_SCALE.get(subtype, 1.0)
        name = row["name"] + ".wav"
        path = os.path.join(out, name)
        if subtype in FULL_SCALE and subtype != "PCM_32":
            sf.write(path, data << (32 - {"PCM_16": 16, "PCM_24": 24}[subtype]), sr, subtype=subtype)
        else:
            sf.write(path, data, sr, subtype=subtype)
        with open(path, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        m = NAME.match(row["name"])
        is_room = m.group(1) == ROOM_TONE
        values, flags = checks(data / scale, sr, fade_out > 0, None if is_room else room_db)
        if is_room:
            flags = [f for f in flags if f == "clipped"]
        files.append({
            "file": name, "id": m.group(1), "strength": None if m.group(2) == "-" else m.group(2), "take": int(m.group(3)),
            "sha256": digest, "duration": round(len(data) / sr, 6), "sampleRate": sr, "sampleFormat": subtype,
            "channels": int(data.shape[1]),
            "from": {"file": os.path.basename(row["file"]), "start": round(float(row["start"]), 9),
                     "length": round(float(row["length"]), 9)},
            "fades": {"in": fade_in, "out": fade_out} if (fade_in or fade_out) else None,
            "levels": values, "flags": flags,
        })

    doc = {
        "format": FORMAT, "version": FORMAT_VERSION,
        "generator": {"name": "listener", "version": __version__},
        "created": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rule": "Each file holds the raw recording's own samples for the take: no gain, resampling or dither. Where 'fades' is set, a linear fade of that many seconds was applied at that end.",
        "session": session,
        "roomTone": None if room_db is None else {"file": room[0][0]["name"] + ".wav", "rms": round(room_db, 2)},
        "flags": {
            "clipped": "peak above -0.5 dBFS with three or more samples in a row at the maximum",
            "hot": "peak above -3 dBFS",
            "starts-loud": "within 20 dB of the peak in the first 2 ms: the attack may be cut off",
            "ends-loud": "within 40 dB of the peak in the last 5 ms and no fade: the tail is cut off",
            "dc-offset": "mean within 40 dB of the peak",
            "near-room-tone": "peak less than 40 dB above the room tone's RMS",
        },
        "files": files,
        "refused": refused,
    }
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return doc


def summary_text(doc: dict) -> str:
    lines = [f"{len(doc['files'])} takes written, {len(doc['refused'])} refused"]
    if doc["roomTone"]:
        lines.append(f"room tone: {doc['roomTone']['rms']:.1f} dBFS RMS")
    else:
        lines.append("no room tone take (roomtone_-_01): levels above the room cannot be given")
    for f in doc["files"]:
        if f["flags"]:
            lines.append(f"  {f['file']}: {', '.join(f['flags'])} (peak {f['levels']['peak']:.1f} dBFS)")
    for r in doc["refused"]:
        lines.append(f"  refused {r['name']}: {r['why']}")
    return "\n".join(lines) + "\n"
