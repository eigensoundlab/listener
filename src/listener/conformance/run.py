# SPDX-License-Identifier: Apache-2.0
"""`listener conform`: run the suites, summarise, and write golden fixtures for Playhead's tests."""
from __future__ import annotations

import datetime
import json
import os

from .. import __version__
from ..measure import implementations
from . import din45692, ebu, iso532, reference_tones


def run(iso: str | None = None, din: str | None = None, ebu_folder: str | None = None, ecma_python: str | None = None,
        fixtures: str | None = None, ebu=None) -> dict:  # `ebu` kept for the command line's keyword
    from . import ebu as ebu_mod
    ebu_folder = ebu_folder or (ebu if isinstance(ebu, str) else None)
    cases = []
    cases += ebu_mod.cases(48000)
    cases += ebu_mod.programme_cases(ebu_folder)
    cases += reference_tones.cases(ecma_python)
    if iso:
        cases += iso532.cases(iso)
    else:
        cases.append({"suite": "iso532-1", "case": "Annex B.4 and B.5", "pass": None,
                      "skipped": "needs the standard's signals: listener conform --iso532-1 <folder>"})
    if din:
        cases += din45692.cases(din)
    else:
        cases.append({"suite": "din45692", "case": "test signals", "pass": None,
                      "skipped": "needs the standard's signals: listener conform --din45692 <folder>"})
    ran = [c for c in cases if c.get("pass") is not None]
    doc = {
        "format": "listener-conformance", "version": 1,
        "generator": {"name": "listener", "version": __version__},
        "created": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "implementations": implementations(ecma_python),
        "passed": all(c["pass"] for c in ran),
        "counts": {"passed": sum(1 for c in ran if c["pass"]), "failed": sum(1 for c in ran if not c["pass"]),
                   "skipped": len(cases) - len(ran)},
        "cases": cases,
    }
    if fixtures:
        write_fixtures(doc, fixtures)
    return doc


def write_fixtures(doc: dict, folder: str) -> None:
    """Fixtures another implementation (Playhead's JavaScript) can test itself against.

    They hold recipes and expected numbers, never the standards' own files.
    """
    from . import ebu as ebu_mod
    os.makedirs(folder, exist_ok=True)
    head = {"generator": doc["generator"], "created": doc["created"],
            "regenerate": "listener conform --iso532-1 <folder> --din45692 <folder> --ecma --fixtures <this folder>"}
    with open(os.path.join(folder, "ebu-tech-3341-3342.json"), "w", encoding="utf-8") as fh:
        json.dump({"format": "listener-fixture", "version": 1, **head, **ebu_mod.fixture(),
                   "oracle": [c for c in doc["cases"] if c["suite"].startswith("tech33") and c.get("pass") is not None]},
                  fh, indent=1)
    iso_cases = [c for c in doc["cases"] if c["suite"] == "iso532-1" and c.get("pass") is not None]
    if iso_cases:
        with open(os.path.join(folder, "iso532-1-annex-b.json"), "w", encoding="utf-8") as fh:
            json.dump({"format": "listener-fixture", "version": 1, **head,
                       "source": "ISO 532-1:2017 Annex B.4 and B.5. The signals are not included: they come with the standard. 16-bit files need a factor of 2*sqrt(2) to be in Pa.",
                       "tolerance": "N(t) within 5 % or 0.1 sone of the standard's curve for at least 99 % of the time; Nmax and N5 here to 5 %",
                       "signals": iso_cases}, fh, indent=1)
    din_cases = [c for c in doc["cases"] if c["suite"] == "din45692" and c.get("pass") is not None]
    if din_cases:
        with open(os.path.join(folder, "din45692.json"), "w", encoding="utf-8") as fh:
            json.dump({"format": "listener-fixture", "version": 1, **head,
                       "source": "DIN 45692:2009 test signals (not included). Tolerance 5 % or 0.05 acum.",
                       "signals": din_cases}, fh, indent=1)
    tones = [c for c in doc["cases"] if c["suite"] == "reference-tones"]
    with open(os.path.join(folder, "reference-tones.json"), "w", encoding="utf-8") as fh:
        json.dump({"format": "listener-fixture", "version": 1, **head,
                   "source": "The sounds that define each unit; build them from the text in each case.",
                   "signals": tones}, fh, indent=1)


def summary_text(doc: dict) -> str:
    lines = []
    suites: dict[str, list] = {}
    for c in doc["cases"]:
        suites.setdefault(c["suite"], []).append(c)
    for suite, cs in suites.items():
        ok = sum(1 for c in cs if c.get("pass") is True)
        bad = [c for c in cs if c.get("pass") is False]
        skip = sum(1 for c in cs if c.get("pass") is None)
        lines.append(f"{suite:16s} passed {ok:3d}  failed {len(bad):2d}  skipped {skip:2d}")
        for c in bad:
            lines.append(f"    FAILED case {c['case']}: expected {c.get('expected')}, measured {c.get('measured')} {c.get('error', '')}")
    lines.append("ALL PASSED" if doc["passed"] else "FAILURES")
    return "\n".join(lines) + "\n"
