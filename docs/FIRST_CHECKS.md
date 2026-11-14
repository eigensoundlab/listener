# First checks

listener 0.1.0, run on 10 November 2026. Every number here comes from `tools/first_checks.sh` and
`tools/summarise.py`; the result files are in `results/2026-11-10/` (all but `conformance.json`: see the end).

Versions: Python 3.13, MoSQITo 1.2.1 (signals from its repository at d990c33), pyloudnorm 0.2.0, sottek-hearing-model
0.1.14, Playhead 0.3.0 at 7492a1f, the 56 CC0 Sonic Pi samples of Playhead's `experiments/corpus/summary.csv`.

## The brief's first checks

| Check | Result |
|---|---|
| ISO 532-1 Annex B.4 within its tolerances | **Passed**, with B.5 as well: 20 of 20 signals. N(t) inside the 5 % band all the time; largest Nmax error 0.0007 sone |
| EBU test set within its stated limits | **Passed for the 25 cases the documents define by a formula** (Tech 3341 cases 1 to 6 and 9 to 23, Tech 3342 cases 1 to 4), built from the documents' tables. **Not run:** the 4 programme recordings (Tech 3341 cases 7 and 8, Tech 3342 cases 5 and 6): they need the EBU's own files, which this session's shell could not fetch (it reaches only package registries and GitHub) |
| DIN 45692 test signals | **Passed**: 41 of 41 with the stationary method; listener's per-frame median is inside tolerance for all 41 too (largest deviation 0.15 acum) |
| Unit-defining tones | 1 sone 1.000; 1 acum 0.980; 1 sone_HMS 1.000; 1 asper_HMS 1.041. 1 vacil not run: no open implementation of ECMA-418-2 Clause 9 |
| The 56 effects: BS.1770 against ISO 532-1 "up to about 17 dB, mostly on bass and tonal sounds" | **Reproduced.** Computed the earlier pilot's way: range 17.8 dB against LUFS-I, 17.5 dB against Max M. In dB of gain with a stated ear convention: 15.5 to 19.5 dB. Same sounds at the two ends |
| Pilot protocol and stimulus list written, reviewed before anyone listens | **Draft written, awaiting review**: `docs/PILOT_PROTOCOL.md` |

Two more results the brief asked for under "conformance":

- **Playhead passes EBU Tech 3341 on the same cases.** A drop-in test for Playhead's `test/` folder
  (`fixtures/playhead/ebu-conformance-test.js`, with the recipes in `ebu-tech-3341-3342.json`) runs 28 checks on
  Playhead 0.3.0: all pass, largest deviation 0.04 LU. Playhead's and listener's integrated loudness, Max M and
  Max S agree within 0.05 dB on all 56 effects, file and sounding span; the 0.04 dB between them is pyloudnorm's
  filter design, which reads a 1 kHz tone 0.035 dB low.
- **Playhead's simplified ISO 532-1 against the full method.** On a 1 kHz tone it is within 6 % in sone from 40 to
  80 dB SPL. On white noise it reads 2.6 to 2.7 times the sone (about 14 phon), which is the size of its calibration
  constant (kN = 2.69): the constant probably makes up on the tone for the missing slopes between bands, and sounds
  that fill the bands get it on top. On the 56 effects its maximum is a median 3.3 times the full method's (17 phon), and
  after removing that offset single files still differ by −10 to +14 phon; rank correlation 0.72 for the maximum,
  0.86 for the 95th percentile. As a curve for display this may not matter. As a loudness in sone it is not ISO 532-1.

## What the checks turned up

**In Playhead's repository**

1. **`experiments/levels/measures.py` does not K-weight its Max M and Max S.** Its `kweight()` passes a (frames,
   channels) array to pyloudnorm's `apply_filter`, which filters along the last axis: across the channels. A mono file
   only gets a gain of 3.65 dB; in a stereo file the filter mixes the two channels. The script's stored values are reproduced
   exactly that way (`drum_heavy_kick`: −10.09); filtered per channel the value is −16.06, and Playhead's own is
   −16.02. Playhead's JavaScript is not affected, nor are the script's LUFS-I and Zwicker columns. Affected: its
   `lufs_m`, `lufs_s`, `ev_main` and `by_class`, and what the guide quotes from them. In particular, "with Zwicker
   standing in for listeners, LUFS-I evens the set best (4.4 to 4.7 dB against 5.5 for Max M)" does not hold: with
   the corrected values the ISO 532-1 spread left after normalising is 4.5 to 4.6 dB for Max M, 4.6 for peak, 4.7
   to 4.8 for LUFS-I, 4.9 to 5.0 for Max M over the loudest event, 5.4 to 5.6 for Max S and 5.9 to 6.0 for RMS.
   Four of the six are level.
2. **Two span rules disagree with each other.** A span under 0.4 s counts as a window with silence around it for
   Max M, and as its own mean for integrated loudness. A 50 ms impulse then reads 9 dB higher in `integrated@event`
   than in `momentaryMax@event`, and 9 dB higher than the same impulse reads once the file goes on (the "slow train"
   row below). Worth one rule for both.

**In the tools the brief relies on**

3. **pyloudnorm 0.2.0 counts a partial last block.** It rounds the number of 0.4 s blocks instead of rounding down,
   so a file a little over 0.4 s gets a block that runs past its end. Nine of the 56 effects were affected, by up to
   2.15 dB (`elec_wood`, 0.478 s). listener gates on complete blocks itself and uses pyloudnorm for the filter and
   the loudness range; a test holds both behaviours.
4. **MoSQITo 1.2.1 reads the last frame as the state before the first** in its nonlinear-decay stage (index −1).
   The first frames of N(t) then depend on how the signal ends. listener always ends the signal in 0.5 s of
   silence, which removes it.
5. **sottek-hearing-model 0.1.14 is `AGPL-3.0-only`** in its package metadata, not GPL-3 as the notes say. It runs
   as a separate process here either way; the one file that imports it carries its licence.
6. **ISO 532-1 signal 15 (vehicle interior) is a diffuse-field case.** Run as free field it fails; the suite reads
   the field from the standard's spreadsheet.

**About single values for short sounds**

7. **ISO 532-1's own N5 values follow no single rule.** For its long signals N5 leaves out the first 100 ms and the
   last 500 ms. For the tone pulses of 10 and 50 ms it is taken over the whole file; for the hammer, ratchet and
   woodpecker without the first 100 ms only; for the 500 ms pulse and the combined pulses none of the three rules
   gives the standard's number. For the 10 ms pulse the three rules give 0.74, 0.22 and 0.32 sone. A percentile of
   a short sound mostly measures the silence that was counted.
8. **The Zwicker curve peaks up to 6 ms after a short sound has ended.** A maximum taken strictly inside a 5 ms
   event reads 0.36 sone where the curve reaches 1.58. Spans are read 20 ms past their end.
9. **ECMA-418-2's own single value is not usable on one-shots**, as the notes found: on `elec_blip` at the 70 dB level its
   power average is 4.6 sone_HMS where the curve's maximum is 8.1. `listener measure` gives maximum and 90th percentile
   per event and labels the standard's value.

## Where the measures part on the 56 effects

Gains in dB each measure would give a file to make the set equally loud, set median removed. ISO 532-1 is solved for
the gain it implies, after each file is brought to −23 LUFS by its Max M and played at the stated level. A mono file
counts as heard in both ears (+3.01 dB in BS.1770); 18 of the 56 are mono.

| Pair | Range | 5th to 95th percentile |
|---|---|---|
| Max M against ISO 532-1 maximum, 60 dB level | 16.9 dB | 14.3 dB |
| Max M against ISO 532-1 maximum, 80 dB level | 15.5 dB | 14.6 dB |
| The same without the ear convention (files as stored), 80 dB level | 18.5 dB | 15.9 dB |
| LUFS-I against ISO 532-1 maximum, 80 dB level | 19.4 dB | 14.7 dB |
| LUFS-I against Max M | 12.9 dB | 8.0 dB |
| Peak against LUFS-I | 22.4 dB | 9.0 dB |
| Peak against Max S | 22.3 dB | 16.4 dB |
| Max M over the file against over the loudest event | 4.5 dB | 2.7 dB |
| ISO 532-1 at the 60 dB level against the 80 dB level | 2.1 dB | 1.4 dB |

The two ends (ISO 532-1 minus Max M: positive means the hearing model would turn the file up more than Max M does):

| File | 60 dB level | 80 dB level | Event (s) | Share below 150 Hz | Class | Channels |
|---|---|---|---|---|---|---|
| drum_snare_hard | -7.0 | -6.1 | 0.22 | 0.01 | impulse | mono |
| loop_amen | -6.4 | -6.0 | 0.21 | 0.40 | impulse | stereo |
| vinyl_hiss | -6.5 | -5.8 | 0.19 | 0.48 | impulse | stereo |
| vinyl_scratch | -6.2 | -5.7 | 0.11 | 0.55 | impulse | mono |
| misc_burp | -6.2 | -5.5 | 0.43 | 0.09 | iterative | mono |
| misc_cineboom | -5.9 | -5.4 | 6.91 | 0.88 | sustained | stereo |
| … | | | | | | |
| ambi_drone | +6.5 | +6.4 | 3.13 | 0.00 | sustained | stereo |
| ambi_glass_hum | +5.8 | +6.6 | 9.40 | 0.00 | sustained | stereo |
| bass_hit_c | +6.6 | +7.5 | 0.26 | 0.82 | iterative | stereo |
| perc_bell | +7.7 | +8.1 | 1.33 | 0.00 | sustained | stereo |
| drum_heavy_kick | +8.4 | +8.7 | 0.23 | 0.98 | impulse | mono |
| ambi_lunar_land | +7.9 | +9.1 | 7.40 | 0.00 | sustained | stereo |
| ambi_piano | +9.9 | +9.4 | 0.74 | 0.98 | sustained | stereo |
| bass_woodsy_c | +8.9 | +9.4 | 3.23 | 0.96 | sustained | stereo |

- **The pattern is the pilot's**: bass, drones, a bell and a piano note at one end (ISO 532-1 hears them 6 to 10 dB
  quieter than Max M does), short bright noisy hits at the other (up to 7 dB louder).
- **Playback level matters less here than the notes suggest.** Between the 60 and 80 dB levels the ISO 532-1 gain of
  a file moves by −0.5 to +1.6 dB (standard deviation 0.4 dB), and one dB of gain is worth 0.88 to 1.10 phon. The
  8 phon swing in the notes belongs to a synthetic 30 to 150 Hz boom against a click over 40 dB of level: the
  benchmark below gives 3.9 dB for that contrast between 60 and 80 dB SPL. So level is a first-order factor for
  sub-bass one-shots and a second-order one for the rest of this set.
- **The ear convention is worth 3 dB of the headline number** on a set that mixes mono and stereo files.
- ECMA-418-2 was not run over the 56 effects (about half an hour of computing); it was run on the benchmark, on its
  reference tones and on single files.

**What `listener disagree --pick 24` would put in front of listeners from this set** (to show the method; the pilot
needs a sound-effects corpus, which this set is not):

| File | Duration of the loudest event | Low-frequency | Long tail | Spread over all measures (dB) |
|---|---|---|---|---|
| drum_heavy_kick | 50 to 400 ms | yes | no | 17.9 |
| vinyl_hiss | 50 to 400 ms | yes | yes | 17.1 |
| bass_woodsy_c | over 2 s | yes | yes | 14.4 |
| ambi_piano | 0.4 to 2 s | yes | yes | 14.1 |
| elec_blip | 50 to 400 ms | no | no | 12.9 |
| perc_bell | 0.4 to 2 s | no | no | 11.5 |
| ambi_drone | over 2 s | no | yes | 11.3 |
| vinyl_rewind | 0.4 to 2 s | no | yes | 8.0 |
| loop_industrial | 0.4 to 2 s | yes | no | 6.9 |
| guit_harmonics | over 2 s | no | no | 4.1 |
| drum_roll | 50 to 400 ms | no | yes | 3.4 |
| bass_hit_c | 50 to 400 ms | yes | no | 13.9 |
| loop_garzul | 50 to 400 ms | yes | yes | 6.3 |
| misc_cineboom | over 2 s | yes | yes | 6.1 |
| guit_em9 | 0.4 to 2 s | yes | yes | 4.8 |
| elec_ping | 50 to 400 ms | no | no | 11.6 |
| misc_burp | 0.4 to 2 s | no | no | 9.2 |
| ambi_glass_hum | over 2 s | no | yes | 10.1 |
| drum_splash_hard | 0.4 to 2 s | no | yes | 7.2 |
| glitch_perc2 | 0.4 to 2 s | yes | no | 6.7 |
| loop_breakbeat | 50 to 400 ms | yes | no | 12.0 |
| glitch_bass_g | 50 to 400 ms | yes | yes | 5.7 |
| ambi_haunted_hum | over 2 s | yes | yes | 5.9 |
| drum_snare_hard | 50 to 400 ms | no | no | 10.0 |

## Published loudness phenomena against the measures

*This is the benchmark's first revision (10 November 2026), with stimuli rebuilt from the research notes. On 14
November the papers were read and the benchmark revised to eighteen results: `results/literature-model/phenomena.md`
and `docs/LITERATURE_MODEL.md`. The largest change for the standard measures: with the levels the paper names, the
ISO 532-1 maximum reads 11.8 dB for the largest temporal integration of a tone, where this table has 9.0.*

Each value: the dB by which a measure would raise sound B to make it as loud as sound A, beside what listeners did.
Blank: within 1 dB of the published range, or the right sign. ~: within 3 dB. ✗: further, no effect, or the wrong sign.

| Phenomenon | Listeners | Peak | RMS | LUFS-I | Max M | Max S | ISO 532-1 Nmax | ISO 532-1 N5 | ECMA-418-2 max |
|---|---|---|---|---|---|---|---|---|---|
| Temporal integration, 1 kHz tone, moderate level | 18 to 19 | +0.0 ✗ | +1.0 ✗ | +1.0 ✗ | +16.2 ~ | +16.2 ~ | +9.0 ✗ | +9.0 ✗ | +29.5 ✗ |
| Temporal integration, 1 kHz tone, high level | 9 to 11 | +0.0 ✗ | +1.0 ✗ | +1.0 ✗ | +16.2 ✗ | +16.2 ✗ | +11.1 | +11.2 | +22.6 ✗ |
| Temporal integration, broadband noise, moderate level | 18 to 19 | +2.3 ✗ | +0.9 ✗ | +0.9 ✗ | +16.1 ~ | +16.1 ~ | +17.3 | +17.3 | +36.5 ✗ |
| Temporal integration, broadband noise, high level | 12 to 14 | +2.3 ✗ | +0.9 ✗ | +0.9 ✗ | +16.1 ~ | +16.1 ~ | +17.9 ✗ | +17.9 ✗ | +28.2 ✗ |
| A rising tone is louder than the same tone falling | 3.1 to 5.3 | +0.0 ✗ | +0.0 ✗ | +0.0 ✗ | +0.0 ✗ | +0.0 ✗ | +1.4 ~ | +0.8 ~ | +0.5 ~ |
| An impact-like envelope is softer than its time reverse (tone) | negative (-3 to -1) | +0.0 ✗ (none) | +0.0 ✗ (none) | +0.0 ✗ (none) | +0.0 ✗ (none) | +0.0 ✗ (none) | -4.8 | -3.5 | -2.1 |
| An impact-like envelope is softer than its time reverse (noise) | negative (-3 to -1) | +0.0 ✗ (none) | +0.0 ✗ (none) | +0.0 ✗ (none) | +0.0 ✗ (none) | +0.0 ✗ (none) | -4.9 | -3.8 | -1.9 |
| A slow train of impulses is as loud as one impulse | -1 to 1 | +0.0 | +17.3 ✗ | +9.0 ✗ | +0.0 | +0.0 | +0.0 | +41.4 ✗ | -0.2 |
| A fast train of impulses is louder than one impulse | negative | +0.0 ✗ (none) | +5.7 ✗ (opposite) | +6.0 ✗ (opposite) | -3.0 | -10.0 | -0.4 ✗ (none) | +0.0 ✗ (none) | -1.0 |
| A 63 Hz octave band of noise against a 1 kHz band | 9 to 11 | +0.1 ✗ | +0.0 ✗ | +3.6 ✗ | +1.6 ✗ | +3.6 ✗ | +11.5 | +12.8 ~ | +18.4 ✗ |
| A louder beginning counts for more than a louder middle | positive | -0.8 ✗ (opposite) | -0.1 ✗ (none) | -1.2 ✗ (opposite) | -0.2 ✗ (none) | -0.1 ✗ (none) | -2.0 ✗ (opposite) | -2.5 ✗ (opposite) | -1.8 ✗ (opposite) |
| **Agrees (near)** | | **1** (0) of 11 | **0** (0) of 11 | **0** (0) of 11 | **2** (3) of 11 | **2** (3) of 11 | **6** (1) of 11 | **4** (2) of 11 | **4** (1) of 11 |

- **No measure reproduces more than 6 of the 11.** ISO 532-1's maximum does best; LUFS-I and RMS reproduce none.
- **Nothing has onset weighting.** The last row is wrong or absent for every measure, and the two hearing models
  predict the opposite of what listeners do.
- **Energy measures cannot tell a sound from its time reverse**: exactly 0 dB on three rows where listeners hear 1 to
  5 dB.
- **Max M's 0.4 s window gives 16 dB of temporal integration at every level.** Listeners need 18 to 19 dB at moderate
  levels and 10 to 13 dB at high ones. ISO 532-1 gives 9 dB on tones at a moderate level: half of what listeners need.
- **ECMA-418-2 penalises a 5 ms sound by 23 to 37 dB.** Its blocks are too long for sounds this short.
- **Whole-file statistics fail on trains**: RMS, LUFS-I and N5 want the slow train 9 to 41 dB louder than the single
  impulse it is as loud as.
- A check on the rebuilt stimuli: for the 63 Hz band this run's LUFS-I gives 3.6 dB where the paper reports 2.73 dB
  for BS.1770, so the bands differ somewhat from the paper's.

**Contrasts nobody has measured: each measure's prediction, on record before the listening test**

| Contrast | Peak | RMS | LUFS-I | Max M | Max S | ISO 532-1 Nmax | ISO 532-1 N5 | ECMA-418-2 max | Spread |
|---|---|---|---|---|---|---|---|---|---|
| The same impact dry and with a 2 s reverberant tail | -1.4 | +4.7 | +3.6 | -3.4 | -3.5 | -2.2 | -1.1 | -4.6 | 9.3 |
| A 30-150 Hz boom against a 2-6 kHz click, around 60 dB SPL | +7.0 | +11.2 | +17.2 | +1.1 | +0.7 | +16.8 | +20.0 | +18.7 | 19.3 |
| A 30-150 Hz boom against a 2-6 kHz click, around 80 dB SPL | +7.0 | +11.2 | +17.2 | +1.1 | +0.7 | +12.9 | +16.1 | +13.1 | 16.5 |

The measures part by 9 dB on whether a reverberant tail makes an impact louder or quieter, and by 16 to 19 dB on a
boom against a click. These are the items the pilot is built around.

## Not done

- The four EBU programme items (needs the EBU's files), ISO 532-3 (needs the standard's code), fluctuation strength.
- ECMA-418-2 over the whole test set.
- The fixtures are in `fixtures/` here, not yet in Playhead's `test/`: that is a change to Playhead's repository.
  The ISO 532-1 and DIN 45692 fixtures and `conformance.json` hold the standards' reference numbers (no signals).
  `listener conform` writes them; they are not committed until the terms for republishing them are checked.
- A JavaScript port of the full ISO 532-1.
- Any fitted model. See `docs/MODEL.md`.
