# Output formats

All files are JSON with `format`, `version`, `generator`, `created` and `implementations` (which tool and version
produced each family of numbers). Numbers that depend on the playback level sit under the level's id.

## `listener-measures`, version 1 (`listener measure`)

```json
{
  "format": "listener-measures", "version": 1,
  "calibration": {
    "convention": "The digital signal is what reaches each ear; a mono file is heard in both ears. ...",
    "levels": [{ "id": "spl80", "refSpl": 80, "refLufs": -23, "fullScaleSineSpl": 99.99, "paPerFullScale": 2.825075,
                 "text": "A 1 kHz sine at -23 LUFS (one channel) plays at 80 dB SPL; a full-scale sine plays at 100.0 dB SPL." }]
  },
  "implementations": { "bs1770": "...", "iso532_1": "...", "din45692": "...", "ecma418_2": null, "iso532_3": null },
  "domains": { "iso532_1": { "validatedOn": "...", "outside": "...", "level": "..." } },
  "notes": { "momentary-padded": "span under 0.4 s: Max M counts the span as one window with silence around it" },
  "files": [{
    "path": "impact.wav", "duration": 1.84, "sampleRate": 48000, "channels": 1,
    "peak": -3.1, "truePeak": -2.9, "loudnessRange": null,
    "ears": "both ears hear the same signal",
    "playhead": { "version": "0.3.0", "document": "impact.playhead.json", "events": 2,
                  "listenerMinusPlayhead": { "momentaryMax@file": -0.04 } },
    "spans": [{
      "id": "event:0", "kind": "event", "start": 0.012, "end": 0.41, "class": "impulse", "loudest": true, "decayEnd": 0.38,
      "bs1770": { "peak": -3.1, "rms": -17.6, "integrated": -18.1, "momentaryMax": -18.8, "shortTermMax": -27.6 },
      "byLevel": { "spl80": {
        "iso532_1": { "nMax": 28.02, "n5": 27.6, "levelMax": 88.09, "level5": 87.87 },
        "din45692": { "atNMax": 2.10, "median": 2.34, "p95": 3.19, "gate": "frames with N >= 0.25 Nmax of the span" },
        "ecma418_2": { "loudnessMax": 12.74, "loudness90": 12.52, "tonalityMax": 2.66, "roughnessMax": 0.21, "roughness90": 0.21 }
      } },
      "notes": ["integrated-single-block", "momentary-padded", "short-term-padded"]
    }]
  }]
}
```

- **Spans.** `file` always; `active` (Playhead's `soundStart` to `soundEnd`) and one `event:<i>` per Playhead event when
  the file's `.playhead.json` is found (`--playhead-docs`, or next to the file). Without a document the file gets the
  note `no-playhead-document`.
- **Level-free measures** (`bs1770`): sample peak and RMS in dBFS; integrated, momentary maximum and short-term maximum
  in LUFS, as a meter reads the file (channels' power summed, a mono file counted once). The span rules are Playhead's
  (docs/LEVELS.md in Playhead), and `playhead.listenerMinusPlayhead` gives the difference to Playhead's own values.
- **Per level** (`byLevel.<id>`): ISO 532-1 maximum and N5 in sone and as loudness level in phon; DIN 45692 sharpness
  at the loudest frame, its median and its 95th percentile over the frames at least a quarter as loud as the span's
  maximum; with `--ecma`, ECMA-418-2 loudness (maximum and 90th percentile, in sone_HMS), tonality and roughness. The
  standard's own single values appear on the `file` span only, labelled: they skip about the first 300 ms.
  `literatureL0.level` is the literature model's event loudness level in dB (docs/LITERATURE_MODEL.md).
- **Ears.** The hearing models take ear signals. A mono file feeds both ears; a stereo file's two channels feed one
  ear each, and the file's loudness is the mean of the two (ISO 532-1) or their quadratic mean (ECMA-418-2).
- **Curves.** `--curves` adds the loudness curves at 100 values a second.
- **ISO 532-3** has a place (`implementations.iso532_3`) and no implementation: none is open, and the standard's code
  comes with its purchase.

## `listener-conformance`, version 1 (`listener conform`)

`cases[]`: `suite` (`tech3341`, `tech3342`, `reference-tones`, `iso532-1`, `din45692`), `case`, `signal`, `expected`,
`tolerance`, `measured`, `pass` (null when skipped, with `skipped` saying what is missing), `source`.
`--fixtures <folder>` writes `listener-fixture` files: recipes and expected numbers another implementation can test
itself against, never the standards' own signals.

## `listener-disagreement`, version 1 (`listener disagree`)

`files[]`, most disputed first: `gains` (dB each measure would give the file to make the corpus equally loud, corpus
median removed), `spread` (largest minus smallest), `isoMinusMaxM` per level, `phonPerDb` (how many phon one dB of
gain is worth for this file), `levelSensitivity`, and `strata` (duration of the loudest event, low-frequency share,
tail, class). `pairs[]`: range and 5th-to-95th percentile of the difference for every pair of measures.
`stimuli[]` with `--pick N`: the most disputed files, spread over the strata.

## `listener-phenomena`, version 1 (`listener phenomena`)

`phenomena[]`: `published` (dB range from the literature) or `expectedSign`, `predictions` per measure (dB by which
the measure would raise sound B to match sound A), `miss`, `verdicts`, `source`, `evidence`, `reconstruction`.
`kind: "open"` marks contrasts with no listener data: predictions only.
Since revision 2 (`revision` at the top): `stimulusFrom` (what was read of the paper), `stimulusHash` (of the two
sounds; ECMA-418-2 values are reused from an earlier file only where it is unchanged), and
`literatureModel.addedAfterFitting`. Rows on temporal integration hold the short sound at the published level and
report how far the equally loud long sound lies under it.

## `listener-recordings`, version 1 (`listener takes`)

`manifest.json` next to the takes: `session` (the session file as given: room, microphone, interface, gain, licence),
`roomTone` (file and RMS), and per file `id`, `strength`, `take`, `sha256`, `duration`, `sampleRate`, `sampleFormat`,
`from` (raw file, start, length), `fades`, `levels` (peak, RMS, how far the start and the end are below the peak, peak
above the room tone) and `flags`. `refused[]` lists rows that were not raw takes, with the reason.

## Planned: `listener-predictions`, version 1

For fitted models: per event a predicted equal-loudness gain with an interval, the model's `domain`, and
`outsideDomain` when the event's descriptors lie outside the listening data the model was fitted on.
