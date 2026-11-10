# SPDX-License-Identifier: Apache-2.0
"""Command line: listener measure | conform | disagree | phenomena | version."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .calibration import DEFAULT_REF_LUFS, parse_levels


def _progress(i, n, name):
    sys.stderr.write(f"\r[{i}/{n}] {name[-60:]:<60}")
    sys.stderr.flush()
    if i == n:
        sys.stderr.write("\n")


def _write(obj, out, pretty):
    text = json.dumps(obj, indent=1 if pretty else None, ensure_ascii=False)
    if out and out != "-":
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        sys.stdout.write(text + "\n")


def _add_levels(p):
    p.add_argument("--levels", default=None,
                   help="playback levels: dB SPL of a 1 kHz sine at --ref-lufs, comma-separated (default 70,80)")
    p.add_argument("--ref-lufs", type=float, default=DEFAULT_REF_LUFS, help="loudness of that reference sine (default -23)")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="listener", description="Measures and reports for the perception of sound effects.")
    sub = ap.add_subparsers(dest="cmd")

    m = sub.add_parser("measure", help="every measure per file and per Playhead event")
    m.add_argument("paths", nargs="+")
    m.add_argument("--playhead-docs", default=None, help="folder of <file>.playhead.json documents (default: next to each file)")
    _add_levels(m)
    m.add_argument("--ecma", action="store_true", help="add ECMA-418-2 through the tool named by LISTENER_ECMA_PYTHON")
    m.add_argument("--ecma-python", default=None)
    m.add_argument("--no-roughness", action="store_true")
    m.add_argument("--curves", action="store_true", help="store the loudness curves (100 values a second)")
    m.add_argument("--jobs", type=int, default=1)
    m.add_argument("--out", default="-")
    m.add_argument("--pretty", action="store_true")

    c = sub.add_parser("conform", help="run the conformance suites and write golden fixtures")
    c.add_argument("--iso532-1", dest="iso", default=None, help="folder with ISO 532-1 Annex B (Annex B.4, Annex B.5 ...)")
    c.add_argument("--din45692", dest="din", default=None, help="folder with the DIN 45692 test signals")
    c.add_argument("--ebu", default=None, help="folder with the EBU loudness test set (for the programme items)")
    c.add_argument("--ecma", action="store_true")
    c.add_argument("--ecma-python", default=None)
    c.add_argument("--fixtures", default=None, help="write golden fixtures for Playhead's tests into this folder")
    c.add_argument("--out", default="-")
    c.add_argument("--pretty", action="store_true")

    d = sub.add_parser("disagree", help="rank files by how much the measures disagree; pick listening-test stimuli")
    d.add_argument("paths", nargs="+")
    d.add_argument("--playhead-docs", default=None)
    _add_levels(d)
    d.add_argument("--jobs", type=int, default=1)
    d.add_argument("--pick", type=int, default=0, help="propose this many stimuli, spread over the strata")
    d.add_argument("--out", default="-")
    d.add_argument("--report", default=None, help="also write a Markdown report")
    d.add_argument("--pretty", action="store_true")

    p = sub.add_parser("phenomena", help="score every measure against published loudness phenomena")
    p.add_argument("--ecma", action="store_true")
    p.add_argument("--ecma-python", default=None)
    p.add_argument("--ecma-from", default=None, help="keep the ECMA-418-2 values of an earlier phenomena file (same version)")
    p.add_argument("--out", default="-")
    p.add_argument("--report", default=None)
    p.add_argument("--pretty", action="store_true")

    sub.add_parser("version")
    a = ap.parse_args(argv)

    if a.cmd == "version":
        print(__version__)
        return 0
    if a.cmd == "measure":
        from . import ecma, measure
        py = ecma.interpreter(a.ecma_python) if (a.ecma or a.ecma_python) else None
        if (a.ecma or a.ecma_python) and not py:
            sys.stderr.write("ECMA-418-2 left out: set LISTENER_ECMA_PYTHON (see external/README.md)\n")
        doc = measure.measure(a.paths, parse_levels(a.levels, a.ref_lufs), a.playhead_docs, py, a.curves,
                              not a.no_roughness, a.jobs, _progress)
        _write(doc, a.out, a.pretty)
        return 0
    if a.cmd == "conform":
        from . import ecma
        from .conformance import run as conform_run
        py = ecma.interpreter(a.ecma_python) if (a.ecma or a.ecma_python) else None
        doc = conform_run.run(iso=a.iso, din=a.din, ebu_folder=a.ebu, ecma_python=py, fixtures=a.fixtures)
        _write(doc, a.out, a.pretty)
        sys.stderr.write(conform_run.summary_text(doc))
        return 0 if doc["passed"] else 1
    if a.cmd == "disagree":
        from . import disagree
        doc = disagree.run(a.paths, parse_levels(a.levels, a.ref_lufs), a.playhead_docs, a.jobs, a.pick, _progress)
        _write(doc, a.out, a.pretty)
        if a.report:
            with open(a.report, "w", encoding="utf-8") as fh:
                fh.write(disagree.report_markdown(doc))
        return 0
    if a.cmd == "phenomena":
        from . import ecma
        from .phenomena import bench
        py = ecma.interpreter(a.ecma_python) if (a.ecma or a.ecma_python) else None
        prior = json.load(open(a.ecma_from, encoding="utf-8")) if a.ecma_from else None
        doc = bench.run(None, py, prior)
        _write(doc, a.out, a.pretty)
        if a.report:
            with open(a.report, "w", encoding="utf-8") as fh:
                fh.write(bench.report_markdown(doc))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
