# The literature model, version L0: what it is and how it does

Built on 14 November 2026. Every number here is written by `tools/fit_literature_model.py` and `listener phenomena`
into `results/literature-model/`. Which published results set the model and which test it was fixed and committed
before fitting: `docs/LITERATURE_SPLIT.md`.

## In short

- It is the first measure here that reproduces the **level dependence of temporal integration**, and it does so
  without a parameter for it: the dependence comes from a published loudness function.
- On the **four held-out numbers** (tone durations at 5 kHz, a frequency it was not set at) its mean miss is
  **3.3 dB**, against 6.9 dB for Max M and 9.5 dB for the ISO 532-1 maximum.
- On the benchmark's eleven results it agrees with 8 (ISO 532-1: 6; Max M: 2). **Seven of those eleven set it**, so that count is not a
  test. On the three it was not set from and could pass, it has the right sign on all three (so has ECMA-418-2; ISO 532-1 two, Max M one).
- It **fails** where the plan hoped for more: no onset weighting (wrong sign, like every other measure), noise at a
  moderate level (14.8 dB where listeners need 18 to 19), and the shortest sounds at 5 kHz.
- It has three fitted parameters, not six. Three of the plan's mechanisms were tried and bought nothing on this data.
- It has never met a listener's judgement of a sound effect. That claim waits for the pilot.

## What it is

One sound in, one number out: the level in dB of a steady 1 kHz tone predicted to be as loud.

1. **K-weighted level** every 0.5 ms, with a low shelf of **-10.8 dB** under 120 Hz on top of K-weighting.
2. **Loudness of each moment** from that level, by a loudness function for a 1 kHz tone that is flattest at moderate
   levels (Buus & Florentine's "inflected exponential" function).
3. **Growth with duration in the loudness domain**: a sound of duration T reaches (T / (T + 74 ms))^0.53 of its
   steady loudness: 0.23 at 5 ms, 0.52 at 30 ms, 0.85 at 200 ms, 0.96 at 1 s.
4. **The maximum** of the result is the sound's loudness.

Step 3 is the equal-loudness-ratio model of Buus, Florentine & Poulsen (1997), made to run on any envelope: a short
and a long sound differ by the same loudness ratio at every level, and how many dB that ratio is worth depends on how
steep the loudness function is at that level. Nothing in the model says "integration is smaller at high levels".

`listener measure` reports it per span and playback level as `literatureL0.level`; `listener phenomena` has it as a
column; `listener.model.literature.matching_gain` gives the gain between two sounds.

## The results that set it

| # | Result | Listeners (dB) | L0 | L0 with this result left out of the fit | Max M | ISO 532-1 maximum |
|---|---|---|---|---|---|---|
| F1 | 1 kHz tone, 5 against 200 ms, 56 dB SPL | 18 to 19 | **18.7** | 18.8 | 16.2 | 9.0 |
| F2 | the same, 100 dB SPL | 9 to 11 | **13.5** | 14.5 | 16.2 | 11.1 |
| F3 | noise, 5 against 200 ms, 76 dB SPL | 18 to 19 | **14.8** | 13.4 | 16.1 | 17.3 |
| F4 | the same, 100 dB SPL | 12 to 14 | **13.0** | 13.0 | 16.1 | 17.9 |
| F5 | 1 kHz tone, 30 against 200 ms, 56 dB SPL | 6 to 8 | **7.8** | 9.9 | 8.3 | 5.1 |
| F6 | 1 kHz tone falling against rising 15 dB | 3.1 to 5.3 | **2.2** | 2.0 | 0.0 | 1.4 |
| F7 | impulses 4 s apart against one | -1 to 1 | **0.0** | 0.0 | 0.0 | 0.0 |
| F8 | 63 Hz octave band against 1 kHz octave band, 75 dB SPL | 9 to 11 | **10.0** | (sets the shelf) | 1.6 | 11.5 |

Fitted: the two numbers of step 3 and the shelf. Left out one at a time, the model still predicts F1, F4 and F7
inside the published range, and misses the others by 1 to 4.6 dB.

## The results that test it

| # | Result | Listeners (dB) | L0 | Max M | ISO 532-1 maximum |
|---|---|---|---|---|---|
| H1 | 5 kHz tone, 50 against 250 ms, most integration over level | about 9 | **7.0** | 7.0 | 4.3 |
| H2 | 5 kHz tone, 10 against 250 ms, most integration over level | about 22 | **19.2** | 14.2 | 9.9 |
| H3 | 5 kHz tone, 2 against 250 ms, most integration over level | about 40 | **31.6** | 22.3 | 19.5 |
| H4 | 5 kHz tone, 2 against 250 ms, 60 dB above threshold (63 dB SPL) | 20 to 25 | **22.3** | 22.3 | 19.3 |
| H5 | reversed envelope against impact-like one, tone | negative (reverse louder); -1 to -3 from one listener | **-5.0** | 0.0 | -4.8 |
| H6 | reversed envelope against impact-like one, noise | negative (reverse louder); -1 to -3 from one listener | **-5.0** | 0.0 | -4.9 |
| H7 | impulses 0.2 s apart against one | negative (train louder) | **-0.9** | -3.0 | -0.4 |

- **H1 to H4** (Buus et al. 1997): the model follows the growth of integration as the short tone gets shorter, which
  an energy window cannot (Max M gives 10 dB per tenfold duration at every level) and ISO 532-1 does less. It still
  falls 8 dB short at 2 ms, and it puts the level of most integration at 30 to 40 dB SPL where
  the paper finds it near 22 to 24: the loudness function it uses is the 1 kHz one, and the paper's 5 kHz function
  is flat from 22 to 63 dB SPL.
- **H5, H6**: the right sign, and about 5 dB where the one listener measured gave 1 to 3. The same as ISO 532-1.
- **H7**: the right sign, weakly.

## What was tried and dropped

Each line is the model with one thing changed, refitted on the same seven results (the shelf's result apart).
The error is the root mean square of the misses, each divided by the half-width of its published range (at least 1 dB).

| Variant | Error | Within 1 dB of the range | Exponent | Half-duration |
|---|---|---|---|---|
| full model | 2.07 | 5 of 7 | 0.53 | 74 ms |
| loudness doubles every 10 dB at all levels | 2.77 | 4 of 7 | 0.30 | 600 ms |
| loudness formed per critical band and summed | 3.56 | 3 of 7 | 0.50 | 600 ms |
| with decay suppression (one more parameter) | 2.05 | 5 of 7 | 0.54 | 73 ms |
| growth with duration as a plain power law (no saturation before 3 s) | 2.29 | 4 of 7 | 0.34 | none |
| a level-dominant mean instead of the maximum (one more parameter) | 2.17 | 4 of 7 | 0.61 | 50 ms |

- **The loudness function matters most.** With loudness doubling every 10 dB at all levels, integration is 15 dB at
  every level and the error rises from 2.07 to 2.77.
- **Decay suppression** (what lies under the running maximum counts for less) lowered the error by 0.02. Dropped.
  The rising-against-falling difference of 2.2 dB comes from the window and the maximum alone.
- **A mean that favours louder moments**, in place of the maximum: no gain; its first version reached its fit by
  letting silence after a short sound dilute the mean, which is the padding problem under another name. Dropped.
- **Loudness formed per critical band and summed**: much worse. The splatter of a 5 ms tone spreads over several
  bands, the sum makes it too loud, and integration for tones falls to 12 dB. This is probably also why ISO 532-1
  gives 9 dB for tones and 17 for noise.
- **Onset weighting** was taken out before fitting (`docs/LITERATURE_SPLIT.md`): as built, it made a steady tone's
  value depend on its duration.

Of the plan's six parameters: integration survived as two numbers; its level dependence needs none; the low shelf
survived; weighting of what follows the peak and carry-over between events were not needed for these results; onset
weighting was not achieved.

## On the whole benchmark

`results/literature-model/phenomena.md` has the table. Agreement out of eleven: literature model 8 (and 1 near),
ISO 532-1 maximum 6 (1), ECMA-418-2 4 (1), ISO 532-1 N5 4 (2), Max M 2 (3), LUFS-I 0, RMS 0.
Read the model's count with its marks: seven rows set it.

## Predictions for what nobody has measured

dB by which the second sound would be raised to match the first. On record before the listening test.

| Contrast | L0 | Max M | LUFS-I | ISO 532-1 | ECMA-418-2 |
|---|---|---|---|---|---|
| The same impact dry and with a 2 s reverberant tail | -2.1 | -3.4 | +3.6 | -2.2 | -4.6 |
| A 30-150 Hz boom against a 2-6 kHz click, around 60 dB SPL | +8.6 | +1.1 | +17.2 | +16.8 | +18.7 |
| A 30-150 Hz boom against a 2-6 kHz click, around 80 dB SPL | +10.0 | +1.1 | +17.2 | +12.9 | +13.1 |

For the boom the model sits between Max M and the hearing models, and its change with level goes the other way from
theirs: it has one fixed shelf where hearing's low-frequency sensitivity changes with level. Treat its low-frequency
predictions as valid near 75 dB SPL only.

## What limits this version

- **Stimuli rebuilt from descriptions.** Only Buus et al. (1997) was read in the paper. Fetching the other papers
  needed an approval that could not be given while this ran; their stimuli and numbers are the research notes'.
- **The loudness function's coefficients were recalled, not read.** Three checks against sources that were read
  hold (1.000 sone at 40 dB SPL; local exponents 0.25 and 0.41 where Buus et al. give about 0.25 and 0.43).
- **Few numbers.** Eight set three parameters. The ranges come from panels of 3 to 16 listeners.
- **Held-out results were seen during development.** The held-out predictions of three discarded variants were
  printed along the way. Every choice between variants was made on the fit set's error alone, and this version's
  held-out results are reported as they came out.
- **One front end.** The same layer on ISO 532-1's loudness has not been built.

## Next

1. Read the remaining papers and replace the rebuilt stimuli and the notes' numbers (the brief's first step).
2. Onset weighting as a separate decision stage for sustained sounds, tested on Pedersen & Ellermeier (2008).
3. A loudness function per frequency region, to move the level of most integration for high tones and for noise.
4. The pilot: this version is the prediction on record.
