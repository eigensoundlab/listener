// SPDX-License-Identifier: Apache-2.0
// Playhead's own (simplified ISO 532-1) loudness in sone per file, for comparison with the full method.
//   node tools/playhead_sone.js <playhead checkout> <folder of sounds>  > playhead-sone.json
// Playhead's calibration: a full-scale sine is 100 dB SPL; multichannel files are analysed as Playhead analyses them.
"use strict";
const fs = require("fs"), path = require("path");
const root = path.resolve(process.argv[2]), dir = process.argv[3];
const A = require(path.join(root, "src/analysis.js")), IO = require(path.join(root, "tools/audio-io.js"));
(async () => {
  const out = {};
  for (const f of fs.readdirSync(dir).filter(f => /\.(flac|wav)$/i.test(f)).sort()) {
    const buf = IO.readAudio(path.join(dir, f));
    const F = await A.extractFeatures(buf, null, {});
    F.cal = await A.calibrate(buf.sampleRate);
    const C = A.computeCurves(F, "sfx", {});
    const n = Array.from(C.raw.Nsone).filter(v => isFinite(v));
    const sorted = n.slice().sort((a, b) => a - b);
    out[f] = { frames: n.length, duration: buf.duration, nMax: sorted[sorted.length - 1], n5: sorted[Math.floor(0.95 * (sorted.length - 1))], kN: F.cal.kN };
    process.stderr.write(".");
  }
  process.stdout.write(JSON.stringify(out, null, 1) + "\n");
  process.stderr.write("\n");
})();
