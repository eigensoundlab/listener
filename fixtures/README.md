# Fixtures

Recipes and expected numbers another implementation can test itself against. Regenerate with
`listener conform --iso532-1 <folder> --din45692 <folder> --ecma --fixtures fixtures`.

| File | Holds |
|---|---|
| `ebu-tech-3341-3342.json` | The EBU cases that are defined by a formula, as recipes, with the expected readings |
| `reference-tones.json` | The sounds that define 1 sone, 1 acum, 1 sone_HMS and 1 asper_HMS |
| `sfx56-cc0.listener-measures.json` | Every measure for the 56 CC0 Sonic Pi samples at two playback levels: golden values on audio anyone can fetch |
| `playhead/` | A test for Playhead's `test/` folder: Playhead against the EBU cases |

`iso532-1-annex-b.json` and `din45692.json` are written by the same command and are **not committed**: they hold the
standards' own reference numbers (no signals), and the terms for republishing those have not been checked. The same
goes for `results/*/conformance.json`.
