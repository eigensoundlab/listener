// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Daniel Sandner
//
// Playhead's BS.1770 measures against EBU Tech 3341 (v4, 2023), Table 1: the cases the document defines by a formula,
// built here from the recipes in ebu-tech-3341-3342.json (written by `listener conform --fixtures`).
// Put both files in Playhead's test/ folder and run: node test/ebu-conformance-test.js   (or pass the Playhead root)
// The programme recordings (cases 7 and 8) need the EBU's own files and are not covered.
"use strict";
const fs = require("fs"), path = require("path");
const root = path.resolve(process.argv[2] || path.join(__dirname, ".."));
const P = require(path.join(root, "src/playhead.js"));
require(path.join(root, "src/levels.js"));
const IO = require(path.join(root, "tools/audio-io.js"));
const fx = JSON.parse(fs.readFileSync(path.join(__dirname, "ebu-tech-3341-3342.json"), "utf8"));
const sr = fx.sampleRate;

const val = (v, i) => typeof v === "string" ? Function("i", "return " + v)(i) : v;   // "-38 + i" in the recipes
function render(parts) {                                // [[dBFS or null, seconds], ...] -> stereo, same phase
  const n = parts.reduce((s, p) => s + Math.round(p[1] * sr), 0), d = new Float32Array(n);
  let o = 0;
  for (const [db, sec] of parts) {
    const len = Math.round(sec * sr), a = db == null ? 0 : Math.pow(10, db / 20);
    for (let i = 0; i < len; i++) d[o + i] = a * Math.sin(2 * Math.PI * 1000 * i / sr);
    o += len;
  }
  return IO.makeBuffer(sr, [d, Float32Array.from(d)]);
}
async function levels(buf) { return (await P.analyze(buf, { profile: "fast" })).summary.levels; }

let failed = 0, count = 0;
function check(name, got, expected, tol) {
  const lo = Array.isArray(tol) ? tol[0] : -tol, hi = Array.isArray(tol) ? tol[1] : tol, d = got - expected;
  const ok = d >= lo - 0.0051 && d <= hi + 0.0051;      // Playhead rounds to 0.01
  count++; if (!ok) failed++;
  console.log((ok ? "PASS " : "FAIL ") + name.padEnd(40) + String(got).padEnd(9) + "expected " + expected);
}

(async () => {
  for (const c of fx.integrated) check("Tech 3341 case " + c.case + " integrated", (await levels(render(c.parts))).file.integrated, c.expected, c.tolerance);
  for (const [key, measure] of [["shortTerm", "shortTermMax"], ["momentary", "momentaryMax"]]) for (const c of fx[key]) {
    if (c.parts) {
      const parts = []; for (let r = 0; r < c.repeat; r++) parts.push(...c.parts);
      check("Tech 3341 case " + c.case + " " + measure, (await levels(render(parts))).file[measure], c.expected, c.tolerance);
    } else for (const i of [0, 7, 13, 19]) {
      const parts = [[null, val(c.silenceBefore, i)], [val(c.tone[0], i), c.tone[1]], [null, val(c.silenceAfter, i)]];
      check("Tech 3341 case " + c.case + " segment " + i + " " + measure, (await levels(render(parts))).file[measure], val(c.expected, i), c.tolerance);
    }
  }
  for (const c of fx.truePeak) {
    const n = Math.round(0.5 * sr), fade = Math.round(0.01 * sr), d = new Float32Array(n);
    for (let i = 0; i < n; i++) d[i] = c.amplitude * Math.sin(2 * Math.PI * i / c.period + c.phaseDeg * Math.PI / 180) * Math.min(1, i / fade, (n - 1 - i) / fade);
    check("Tech 3341 case " + c.case + " true peak", (await levels(IO.makeBuffer(sr, [d, Float32Array.from(d)]))).truePeak, c.expected, c.tolerance);
  }
  console.log(failed ? failed + " of " + count + " FAILED" : "all " + count + " passed");
  process.exit(failed ? 1 : 0);
})();
