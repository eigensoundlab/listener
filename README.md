# listener

Author: Daniel Sandner ([ORCID 0000-0002-1041-814X](https://orcid.org/0000-0002-1041-814X)) · Licence: Apache-2.0 · Status: version 0.1, before the listening test

A listener model for sound effects, built in the order the evidence allows: verified measures first, then the
listening data, then a model fitted to them. It supports the research behind
[Playhead](https://github.com/eigensoundlab/playhead), Kurator, SFX Workbench and the REAPER package.

No published study tests any loudness measure against listeners on sound effects, and the standard measures part by
many dB exactly where effects live: short, low, or with long tails. `listener` does four things about that, and has a method for recording the sounds the listening test needs:

| Command | What it does |
|---|---|
| `listener measure` | Every measure per file and per Playhead event, at stated playback levels: BS.1770 (integrated, Max M, Max S, true peak), ISO 532-1 (maximum, N5), DIN 45692 sharpness, ECMA-418-2 (loudness, tonality, roughness) |
| `listener conform` | Conformance: EBU Tech 3341 and 3342, ISO 532-1 Annex B, DIN 45692, and the tones that define each unit; writes golden fixtures for Playhead's tests |
| `listener disagree` | Where the measures part on a corpus, in dB of gain, and which files to put in front of listeners |
| `listener phenomena` | Every measure against published facts about the loudness of short and changing sounds, and each measure's prediction for the contrasts nobody has measured |
| `listener takes` | Cuts named takes out of raw recordings, sample for sample, and writes their manifest: the last step of the recording method in [recording/](recording/README.md) |

The results of the first run are in [docs/FIRST_CHECKS.md](docs/FIRST_CHECKS.md). A first model, set from published
listener results and tested on others, is in [docs/LITERATURE_MODEL.md](docs/LITERATURE_MODEL.md). The plan for the model is in
[docs/MODEL.md](docs/MODEL.md), the listening test in [docs/PILOT_PROTOCOL.md](docs/PILOT_PROTOCOL.md), the file
formats in [docs/FORMAT.md](docs/FORMAT.md).

## Install

```sh
pip install -e ".[test,conformance]"     # Python 3.11 or later
pytest                                   # about 40 s
```

ECMA-418-2 comes from a tool under a copyleft licence and runs as a separate process in its own environment:
[external/README.md](external/README.md).

## Use

```sh
# Playhead's events for a folder of sounds, then every measure per event at two playback levels
playhead analyze sounds/ --profile sfx --out-dir docs/
listener measure sounds/ --playhead-docs docs/ --levels 60,80 --out measures.json

# the conformance suites; the standards' own signals come from folders you name
listener conform --iso532-1 "<folder with Annex B.4, Annex B.5>" --din45692 <folder> --ecma --fixtures fixtures/

# which files are worth a listener's time
listener disagree sounds/ --playhead-docs docs/ --levels 60,80 --pick 24 --report disagreement.md

# the published phenomena
listener phenomena --ecma --report phenomena.md
```

### Playback level

Loudness in sone depends on how loud the sound is played, so no level is implied. `--levels 60,80` says: a 1 kHz
sine that reads −23 LUFS on a meter (`--ref-lufs`) plays at 60, and at 80, dB SPL. The output also gives the same
mapping as the level of a full-scale sine (80 corresponds to 100 dB SPL, the convention of Playhead and of most
ISO 532-1 tools). Every level-dependent number sits under its level's id.

## Rules this project keeps

1. **No circularity.** A tool is never tuned against a model and then judged by it. A fitted model is scored on
   listeners and items it has not seen.
2. **Every model's domain is stated** in the output (`domains`), and values outside it carry a note.
3. **Disagreement between models is reported**, not averaged away.
4. **Levels are matched before any comparison of two versions of a sound.**
5. **Every number can be regenerated**: `tools/first_checks.sh`, with pinned versions in `pyproject.toml`.
6. **Listener data only with consent**, anonymous, in sessions people join; published in an open format with the
   protocol.
7. **Licences are kept apart.** Copyleft tools run as separate processes; standards' signals are never redistributed.

## What it does not do yet

- **ISO 532-3** (Moore, Glasberg and Schlittenlacher): no open implementation exists; the output has a place for it.
- **ECMA-418-2 fluctuation strength** (4th edition, 2025): no open implementation was found.
- **A model fitted to sound effects.** The literature model (`literatureL0` in the output) is set from published
  results on tones and noises. Version 2 fits an event-level model to the pilot's matches.

## Citing

`CITATION.cff` has the citation. A DOI is added with the first archived release.

## Licence

Apache-2.0, except `external/ecma418_2_worker.py` (AGPL-3.0-only, because the package it imports is). See `NOTICE`.
