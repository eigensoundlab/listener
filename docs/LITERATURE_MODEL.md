# The literature model, version L0: what it is and how it does

Second revision, 14 November 2026: refitted after the papers behind the benchmark were read. The first revision, built the same day on stimuli rebuilt from the research notes, is kept in `results/literature-model/revision-1/`. Every number here is written by `tools/fit_literature_model.py` and `listener phenomena` into `results/literature-model/`, and this file by `tools/report_literature_model.py`. Which published results set the model and which test it: `docs/LITERATURE_SPLIT.md`.

## In short

- **Reading the papers made the model's test result worse, and it is still ahead.** On the four held-out numbers (tone durations at 5 kHz, a frequency it was not set at) its mean miss is **5.0 dB**, against 6.7 dB for Max M and 9.4 dB for the ISO 532-1 maximum. With the rebuilt stimuli it was 3.3 dB.
- **Why it changed.** In the paper the level named for the largest temporal integration is the short sound's. The long sound it matches is then 18 dB lower, where loudness grows most slowly with level. The rebuilt stimuli had both at the named level. With the right levels the loudness function explains more of the effect and the fitted growth with duration is faster (48 ms where it was 74 ms), which costs accuracy between 50 and 250 ms.
- **Six new test results, never fitted**: octave bands of noise from 125 Hz to 8 kHz against the 1 kHz band. The model is within 1 dB of the listeners' range on 5 of 6 (LUFS-I 4, ISO 532-1 3). The listeners' values are derived from the paper's table and carry 1.5 dB of doubt.
- On the benchmark's 18 results it agrees with 13 (ISO 532-1 maximum 8, Max M 7, LUFS-I 4). 8 of them set it. On the 9 that test it: 8 (ISO 532-1 maximum 5, ECMA-418-2 5, LUFS-I 4, Max M 5).
- It still **fails** on onset weighting (wrong sign, like every other measure), on noise at a moderate level, and on the shortest sounds at 5 kHz.
- It has three fitted parameters. It has never met a listener's judgement of a sound effect. That waits for the pilot.

## What it is

One sound in, one number out: the level in dB of a steady 1 kHz tone predicted to be as loud.

1. **K-weighted level** every 0.5 ms, with a low shelf of **-10.7 dB** under 120 Hz on top of K-weighting.
2. **Loudness of each moment** from that level, by a loudness function for a 1 kHz tone that is flattest at moderate
   levels (Buus & Florentine's "inflected exponential" function).
3. **Growth with duration in the loudness domain**: a sound of duration T reaches (T / (T + 48 ms))^0.53 of its
   steady loudness: 0.29 at 5 ms, 0.60 at 30 ms, 0.89 at 200 ms, 0.98 at 1 s.
4. **The maximum** of the result is the sound's loudness.

Step 3 is the equal-loudness-ratio model of Buus, Florentine & Poulsen (1997), made to run on any envelope: a short
and a long sound differ by the same loudness ratio at every level, and how many dB that ratio is worth depends on how
steep the loudness function is at that level. Nothing in the model says "integration is smaller at high levels".

`listener measure` reports it per span and playback level as `literatureL0.level`; `listener phenomena` has it as a
column; `listener.model.literature.matching_gain` gives the gain between two sounds.

## The results that set it

Level difference at equal loudness, dB. "Before": the first revision's model on its rebuilt stimuli.

| # | Result | Listeners | L0 | L0 with this result left out of the fit | Max M | ISO 532-1 maximum | L0 before |
|---|---|---|---|---|---|---|---|
| F1 | 1 kHz tone, 5 against 200 ms, the 5 ms tone at 56 dB SPL | 18 to 19 | **19.8** | 20.5 | 16.0 | 11.8 | 18.7 |
| F2 | the same, the 5 ms tone at 100 dB SPL | 9 to 11 | **12.3** | 12.7 | 16.0 | 11.8 | 13.5 |
| F3 | noise, 5 against 200 ms, the 5 ms noise at 76 dB SPL | 18 to 19 | **14.7** | 13.4 | 16.3 | 15.4 | 14.8 |
| F4 | the same, the 5 ms noise at 100 dB SPL | 12 to 14 | **12.9** | 12.9 | 16.3 | 16.4 | 13.0 |
| F5 | 1 kHz tone, 30 against 200 ms, the 200 ms tone at 37.5 dB SPL | 6 to 8 | **7.7** | 10.4 | 8.2 | 5.2 | 7.8 |
| F6 | 1 kHz tone falling against rising 15 dB | 3.1 to 5.3 | **1.9** | 1.9 | 0.0 | 1.4 | 2.2 |
| F7 | impulses 4 s apart against one | -1 to 1 | **0.0** | 0.0 | 0.0 | 0.0 | 0.0 |
| F8 | 63 Hz octave band against 1 kHz octave band, 75 dB SPL | 9 to 11 | **10.0** | (sets the shelf) | 1.6 | 12.4 | 10.0 |

Fitted: the two numbers of step 3 and the shelf. Left out one at a time, the model still predicts F4, F7 inside the published range, and misses the others by 1.2 to 4.6 dB.
Later studies from the same laboratory, with a different matching procedure, found 26 to 27 dB where F1 has 18 to 19 (Buus, Florentine & Poulsen 1999). F1's range is one study's.

## The results that test it

### Fixed before fitting

| # | Result | Listeners | L0 | Max M | ISO 532-1 maximum | L0 before |
|---|---|---|---|---|---|---|
| H1 | 5 kHz tone, 50 against 250 ms, most integration over level | about 9 | **5.4** | 7.0 | 4.4 | 7.0 |
| H2 | 5 kHz tone, 10 against 250 ms, most integration over level | about 22 | **16.6** | 14.3 | 9.9 | 19.2 |
| H3 | 5 kHz tone, 2 against 250 ms, most integration over level | about 40 | **29.0** | 22.8 | 19.6 | 31.6 |
| H4 | 5 kHz tone, 2 against 250 ms, the 250 ms tone 60 dB above threshold (63 dB SPL) | 20 to 25 | **20.6** | 22.8 | 19.5 | 22.3 |
| H5 | reversed envelope against impact-like one, 330 Hz tone | negative; 1 to 3 dB from one listener | **-3.1** | 0.0 | -1.2 | -5.0 |
| H6 | reversed envelope against impact-like one, noise | negative; 1 to 3 dB from one listener | **-2.8** | +0.1 | -2.8 | -5.0 |
| H7 | impulses 0.2 s apart against one | negative (train louder) | **-0.6** | -3.0 | -0.4 | -0.9 |

- **H1 to H4** (Buus et al. 1997, read in the paper): mean miss 5.0 dB for the model, 6.7 for Max M, 9.4 for the ISO 532-1 maximum. The model follows the growth of integration as the short tone gets shorter. It now reads 5.4 dB for 50 against 250 ms, under the 7 dB of an energy window and the 9 dB of listeners: its growth with duration is nearly over by 50 ms. It puts the most integration with the long tone at 30 dB SPL where the paper finds it near 22 to 24.
- **H5, H6** (Stecker & Hafter 2000, now with the paper's own envelopes, a 330 Hz tone and white noise): the right sign and about the size the one listener gave. The paper found the effect mainly after impact-like sounds.
- **H7**: the right sign, weakly. The paper's stimuli could not be read; these are still rebuilt.

### Added after fitting, never fitted

Fenton & Lee (2017): dB by which listeners raised an octave band of pink noise to match the 1 kHz band at 75 dB.

| # | Result | Listeners (derived) | L0 | LUFS-I | ISO 532-1 maximum |
|---|---|---|---|---|---|
| H8 | 125 Hz octave band against a 1 kHz band | 3.9 to 6.9 | **+5.1** | +1.6 | +8.1 |
| H9 | 250 Hz octave band against a 1 kHz band | 0.6 to 3.6 | **+0.1** | +1.0 | +4.6 |
| H10 | 500 Hz octave band against a 1 kHz band | -3.8 to -0.8 | **+0.3** | +0.8 | +2.3 |
| H11 | 2 kHz octave band against a 1 kHz band | -4.7 to -1.7 | **-1.9** | -2.2 | -3.0 |
| H12 | 4 kHz octave band against a 1 kHz band | -5.8 to -2.8 | **-2.6** | -3.1 | -3.8 |
| H13 | 8 kHz octave band against a 1 kHz band | -3.6 to -0.6 | **-2.6** | -3.2 | +4.0 |

Root mean square miss outside the range: model 0.5 dB, LUFS-I 1.1 dB, ISO 532-1 2.3 dB. Above 250 Hz the model is K-weighting, so there it shares LUFS-I's errors; the shelf fitted at 63 Hz also holds at 125 Hz. Caution: the listeners' values are this project's BS.1770 gain minus the error the paper tabulates, and the paper's one printed BS.1770 value (2.73 dB at 63 Hz) is 0.8 dB under this project's (3.55 dB).

## What was tried and dropped

Each line is the model with one thing changed, refitted on the same seven results (the shelf's result apart).
The error is the root mean square of the misses, each divided by the half-width of its published range (at least 1 dB).

| Variant | Error | Within 1 dB of the range | Exponent | Half-duration |
|---|---|---|---|---|
| full model | 1.93 | 4 of 7 | 0.53 | 48 ms |
| loudness doubles every 10 dB at all levels | 2.72 | 3 of 7 | 0.29 | 600 ms |
| loudness formed per critical band and summed | 3.18 | 4 of 7 | 0.43 | 182 ms |
| with decay suppression (one more parameter) | 1.92 | 5 of 7 | 0.53 | 49 ms |
| growth with duration as a plain power law (no saturation before 3 s) | 2.22 | 5 of 7 | 0.28 | none |
| a level-dominant mean instead of the maximum (one more parameter) | 2.09 | 4 of 7 | 0.48 | 62 ms |

The order is the first revision's. The loudness function matters most (error 1.93 against 2.72 without it); decay suppression and a level-dominant mean buy nothing; loudness formed per critical band and summed is much worse. Onset weighting was taken out before fitting (`docs/LITERATURE_SPLIT.md`). The model's form was chosen on the first revision's stimuli and only refitted here.

## On the whole benchmark

`results/literature-model/phenomena.md` has the table. Agrees (near) of 18: literature model 13 (3); ISO 532-1 maximum 8 (5); Max M 7 (5); Max S 7 (5); ECMA-418-2 maximum 6 (1); ISO 532-1 N5 5 (7); LUFS-I 4 (2); RMS 3 (2); Peak 2 (4).
On the 9 rows that did not set the model: literature model 8 (1); ISO 532-1 maximum 5 (1); Max M 5 (2); Max S 5 (2); ECMA-418-2 maximum 5 (0); ISO 532-1 N5 4 (2); LUFS-I 4 (2); RMS 3 (2); Peak 1 (4).

## Predictions for what nobody has measured

dB by which the second sound would be raised to match the first. On record before the listening test.

| Contrast | L0 | Max M | LUFS-I | ISO 532-1 maximum | ECMA-418-2 maximum | L0 before |
|---|---|---|---|---|---|---|
| The same impact dry and with a 2 s reverberant tail | -1.7 | -3.4 | +3.6 | -2.2 | -4.6 | -2.1 |
| A 30-150 Hz boom against a 2-6 kHz click, around 60 dB SPL | +9.4 | +1.1 | +17.2 | +16.8 | +18.7 | +8.6 |
| A 30-150 Hz boom against a 2-6 kHz click, around 80 dB SPL | +10.5 | +1.1 | +17.2 | +12.9 | +13.1 | +10.0 |

For the boom the model sits between Max M and the hearing models, and its change with level goes the other way from
theirs: it has one fixed shelf where hearing's low-frequency sensitivity changes with level. Treat its low-frequency
predictions as valid near 75 dB SPL only.

## What reading the papers changed

| Paper | What was read | What changed |
|---|---|---|
| Florentine, Buus & Poulsen 1996 | The abstracts. The paper is behind a paywall and the fetch was refused. Gating from Buus et al. 1999, which says the 1996 study used the same | The named level is the 5 ms sound's, so the 200 ms sound is 18 dB lower. The "5 ms" tone is a 13 ms raised-cosine pulse with 5 ms of equivalent duration. Noise bandwidth still unknown |
| Buus, Florentine & Poulsen 1997 | The paper, again | Linear 2 ms ramps, not raised-cosine. The largest integration is with the 250 ms tone near 22 to 24 dB SPL |
| Buus, Florentine & Poulsen 1999 | The paper (new) | Maxima of 26 to 27 dB at 1 kHz with a roving-level procedure; listeners range from 13 to 36 dB |
| Ponsot, Susini & Meunier 2015 | The paper | Nothing in the stimulus. Matching gives 3.2 and 3.4 dB; the asymmetry shrinks for ramps reaching 80 to 90 dB SPL |
| Stecker & Hafter 2000 | The paper | Its own envelope family, a 330 Hz tone and white noise at 80 dB SPL peak, in place of an exponential decay on a 1 kHz tone. One line of the envelope's equation was unreadable in the copy |
| Fenton & Lee 2017 | The paper | 8th-order octave filters; six more bands from its Table 1; its BS.1770 value at 63 Hz differs from this project's by 0.8 dB |
| Fischenich et al. 2021 | The paper | Primacy only for contiguous segments, not when they are 500 ms apart. Stimulus now ten 100 ms segments at 55 dB SPL. The paper says a maximum rule cannot give primacy |
| Pedersen & Ellermeier 2008 | The paper | Listeners given feedback weighted all segments equally; without it, the beginning counted most. That suggests onset weighting is partly a way of listening, which supports modelling it as a separate decision stage |
| Ogura, Suzuki & Sone 1991 | The abstract. The journal's site refuses automated reading of the file | Nothing. Its two rows keep rebuilt stimuli |

## What limits this version

- **Two papers still unread.** Florentine et al. (1996) sets four of the eight fit results and Ogura et al. (1991) one.
- **The loudness function's coefficients were recalled, not read.** Three checks against sources that were read
  hold (1.000 sone at 40 dB SPL; local exponents 0.25 and 0.41 where Buus et al. give about 0.25 and 0.43).
- **One loudness function for all sounds.** It is the 1 kHz tone's. The misses on noise and at 5 kHz point at this.
- **Few numbers.** Eight set three parameters. The ranges come from panels of 3 to 16 listeners, and two studies of
  one laboratory differ by 8 dB on the largest of them.
- **Held-out results were seen during development**, and the model's form was chosen on the first revision's
  stimuli. Every choice between variants was made on the fit set's error alone.
- **The six band results are derived**, not printed in the paper.

## Next

1. The two unread papers: both need a person to open them.
2. A loudness function per frequency region and for noise, to move the level of most integration.
3. Slower growth beyond 50 ms without losing the fit at 5 ms: the form (T / (T + half))^exponent may be too simple.
4. Onset weighting as a separate decision stage for sustained sounds, tested on the weights of Pedersen & Ellermeier
   (2008) and Fischenich et al. (2021).
5. The pilot: this version is the prediction on record.
