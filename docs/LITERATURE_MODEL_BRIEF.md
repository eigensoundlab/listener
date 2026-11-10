# Brief: the literature-constrained event loudness model

For a fresh session. It needs this repository, `docs/MODEL.md` (the plan, section 4 above all), `docs/FIRST_CHECKS.md`
(what the standard measures get wrong) and the project's research note `perception_and_measures.md` (the sources).

## The job

Build the temporal layer of `docs/MODEL.md` as working code, with its parameters set from **published listener
results**, and show on **published results it was not set from** how far it can be trusted. Two uses:

- **A comparison** in every report: beside Max M, LUFS-I and the ISO 532-1 maximum, in `listener phenomena`,
  `listener disagree` and later the pilot's scoring.
- **Usable**: a measure a levelling tool can call for an event, `listener measure` can report, and Playhead could
  port, labelled with its domain.

It may claim that it reproduces the known loudness of short and changing sounds better than the standard measures.
It may not claim to predict the loudness of sound effects: that is the pilot's question, and this model enters the
pilot as the pre-registered prediction.

## What exists

- `listener phenomena` (`src/listener/phenomena/bench.py`): eleven published results and three untested contrasts as
  pairs of sounds; every measure answers "by how many dB would you raise B to match A". A new measure is one more
  entry in `predictions()`. Today's scores: ISO 532-1 maximum 6 of 11, ECMA-418-2 and N5 4, Max M 2, LUFS-I and RMS 0.
- The equal-loudness-gain machinery: `Zwicker.gain_for_level`, the secant solver in the benchmark.
- The front ends: K-weighted pressure (`bs1770.k_weight`), ISO 532-1 N(t) (`zwicker.Zwicker`).

## Steps

1. **Get the papers' own stimuli and numbers.** The benchmark's sounds were rebuilt from the notes' descriptions.
   For each source below, read the paper and record: the exact stimulus (durations, ramps, levels, bandwidth,
   envelope constants), the result at **every** level and duration it reports, the number of listeners and their
   spread. Numbers that exist only in figures are marked as read from a figure, with the reading error. Correct the
   benchmark where it differs; keep the old values in the change log.

   | Result | Source | Needed beyond what the notes give |
   |---|---|---|
   | Duration, 1 kHz tone and noise, 5 / 30 / 200 ms, by level | Florentine, Buus & Poulsen 1996 | The 30 ms data; the whole level function, not two points; ramps |
   | Duration, 5 kHz tone, 2 / 10 / 50 / 250 ms, by level | Buus, Florentine & Poulsen 1997 (full text linked in the notes) | Everything: this is held-out data |
   | Rising against falling tones | Ponsot, Susini & Meunier 2015 | Per level range; both methods |
   | Impact-like envelope against its reverse | Stecker & Hafter 2000 (reprint linked in the notes) | Envelope time constants; sizes per carrier |
   | Onset weights | Fischenich et al. 2021 (open access) | Weight curves, to turn into a predicted level difference |
   | Bowl-shaped weights, 1 s noise in ten segments | Pedersen & Ellermeier 2008 (PDF linked) | Held-out data |
   | Repetition rate of impulses | Ogura, Suzuki & Sone 1991 (open access) | Loudness against rate above the critical rate |
   | Octave bands against 1 kHz | Fenton & Lee 2017 (preprint linked) | All bands, not only 63 Hz; their band definitions |
   | Switched and modulated noise | Zwicker & Zwicker 1991, as used by Moore et al. 2016 (open access) | Held-out data |
   | Collected duration, repetition, asymmetry data | Rennies, Verhey & Fastl 2010 | Whatever is tabulated |

2. **Split before fitting**, and write the split into the repository first. Proposed: fit on Florentine 1996 (both
   carriers, all levels and durations), Ponsot 2015, Ogura 1991 and Fenton & Lee 2017; hold out Buus 1997, Stecker &
   Hafter 2000, Fischenich 2021 (sign and size), Pedersen & Ellermeier 2008 and the switched-noise data. The
   held-out set then tests each mechanism on a paper that did not set it.

3. **Build the layer on the K-weighted front end first** (fast enough to fit; the one a tool can run), then on
   ISO 532-1 N(t). Start from Max M over the event (no parameters) and add one mechanism at a time, in the order of
   `docs/MODEL.md` section 3. Keep every stage switchable.

   A lead worth checking first, for the level dependence of temporal integration. Buus, Florentine & Poulsen (1997),
   as far as this session recalls and to be confirmed in the paper, propose that a short and a long sound differ by
   a constant **loudness ratio**, and that the level difference at
   equal loudness follows from the slope of the loudness function, which is shallowest at moderate levels. A first
   calculation in the session that wrote this brief, with a fifth-order loudness function for a 1 kHz tone **quoted
   from memory and not checked against its paper**, gave slopes of about 0.025 log-sone per dB at 56 dB SPL and 0.041
   at 100 dB SPL: a ratio that would turn 18.5 dB at the moderate level into about 11 dB at the high one, close to
   the published 10, with no free parameter. If the paper's function confirms it, parameter 2 of the plan is not a
   parameter. A single exponential integrator in the loudness domain does not also give the right shape over
   duration (it would be complete by 30 ms); the 30 ms and 5 kHz data decide what replaces it.

4. **Report**, in the repository:
   - the benchmark table with the model's row, fitted and held-out results marked apart;
   - per held-out result: prediction, published value, miss;
   - an ablation table: the score with each mechanism removed;
   - the parameter values with the data that set them, and how many independent numbers stand against how many
     parameters;
   - the model's predictions for the three untested contrasts (dry against wet, boom against click at two levels),
     on record before the pilot;
   - where it fails.

5. **Make it usable.** `listener measure` reports it per event at each playback level, as an equal-loudness gain
   relative to the calibration's reference, under a name that says what it is (for example `eventLoudness.literature`),
   with `domains` text: fitted to which papers, held out on which, never tested on sound effects. `listener disagree`
   and `listener phenomena` include it.

## Rules

- No tuning on the held-out results. If a held-out result is looked at and the model is then changed, say so and
  move that result to the fitted set.
- Nothing from the 56 test effects or any sound-effect corpus goes into the fit. They have no listener data.
- A mechanism that does not lower held-out error is dropped, and the report says it was tried.
- Every number in the report is regenerated by one command.
- If the best honest result is "Max M with a shorter window does about as well", that is the result.

## Done when

- The split, the extracted data with sources, the model, its tests and the report are in the repository.
- `pytest` passes, including a test that the model's benchmark row is reproduced.
- `docs/MODEL.md` is updated with what was found: which of the six parameters survived.
