# SPDX-License-Identifier: Apache-2.0
"""The parts of a file that get their own numbers: the file, its sounding span, and its events.

Event bounds and classes come from the file's Playhead document (`playhead analyze`, schema playhead-analysis v1).
Without one, only the whole file is measured, and the output says so: a whole-file rule misreads one-shots.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass
class Span:
    id: str
    kind: str                 # file | active | event
    start: float
    end: float
    extra: dict = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return self.end - self.start


def find_document(audio_path: str, docs_dir: str | None) -> str | None:
    base = os.path.basename(audio_path)
    stem = os.path.splitext(base)[0]
    for folder in ([docs_dir] if docs_dir else []) + [os.path.dirname(os.path.abspath(audio_path))]:
        for name in (base + ".playhead.json", stem + ".playhead.json"):
            cand = os.path.join(folder, name)
            if os.path.isfile(cand):
                return cand
    return None


def read_document(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if doc.get("schema") != "playhead-analysis":
        raise ValueError(f"{path}: not a playhead-analysis document")
    return doc


def spans_for(duration: float, doc: dict | None) -> tuple[list[Span], dict | None]:
    """Spans of a file and, with a document, what Playhead said about it (for the output's `playhead` block)."""
    spans = [Span("file", "file", 0.0, duration)]
    if not doc:
        return spans, None
    summary = doc.get("summary") or {}
    s0, s1 = summary.get("soundStart"), summary.get("soundEnd")
    if s0 is not None and s1 is not None and s1 > s0:
        spans.append(Span("active", "active", max(0.0, float(s0)), min(duration, float(s1))))
    events = [e for e in (doc.get("events") or []) if e.get("end") is not None and e["end"] > e["start"]]
    loudest = None
    if events:
        loudest = max(range(len(events)), key=lambda i: events[i].get("peakDb") if events[i].get("peakDb") is not None else -999)
    for i, e in enumerate(events):
        extra = {"class": e.get("facture"), "peakDb": e.get("peakDb"), "loudest": i == loudest}
        if e.get("decayEnd") is not None:
            extra["decayEnd"] = float(e["decayEnd"])
        spans.append(Span(f"event:{i}", "event", max(0.0, float(e["start"])), min(duration, float(e["end"])), extra))
    info = {
        "version": (doc.get("generator") or {}).get("version"),
        "profile": doc.get("profile"),
        "assetClass": doc.get("assetClass"),
        "events": len(events),
        "levels": summary.get("levels"),
    }
    return spans, info
