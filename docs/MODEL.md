# The model: what is new, what it rests on, and what would make it worth publishing

The brief says the new parts come from data, not from new formulas. This note reads "data" as
listeners' judgements, published or new, keeps the rule in that sense, and makes the plan concrete enough to
pre-register: what the model outputs, its few parameters and the published fact each one answers
to, how it is fitted and judged, and which additions to the brief would turn a private tool into a contribution others
can build on. Section 5 lists the additions; the first three were built in this version.

## 1. What the field lacks

| Missing | Evidence | What this project can put there |
|---|---|---|
| Listener data on the loudness of sound effects | No dataset found; the nearest (8 technical sounds, two labs) has no public audio | An open set of matches on redistributable audio, raw trials included |
| A measure tested on one-shots | BS.1770 was validated on programme; ISO 532-1 and ISO 532-3 on tones, noises and technical sounds | An event-level measure scored on held-out listeners and items, with the standard measures beside it |
| Agreement on what a short sound's single value is | ISO 532-1's own N5 values for its short test signals follow no single rule (docs/FIRST_CHECKS.md); ECMA-418-2's skip the first 300 ms | A stated event rule, with the padding dependence of the others measured |
| A way to compare measures in the listener's unit | Comparisons are usually phon against dB | Equal-loudness gain in dB for every measure (`listener disagree`) |
| A shared test of what any event-loudness model must reproduce | Each paper tests its own phenomenon | `listener phenomena`: eleven published results and three open contrasts, runnable against any measure |

## 2. What the model outputs

For one event of one file at a stated playback level: **the gain in dB that makes it as loud as the reference**, with
an interval, and whether the event lies inside the data the model was fitted on. The unit is the unit of a listener's
adjustment and of Playhead's levelling. A sone value is an intermediate, never the result.

## 3. Structure: a temporal layer over front ends that already exist

**Front ends (not new, interchangeable).** The loudness-against-time curve comes from one of: the K-weighted power
envelope (BS.1770's filter; cheap, runs in Playhead today); ISO 532-1 N(t); ECMA-418-2 N(t); ISO 532-3 if its code is
bought. The model is fitted and reported per front end. Where front ends disagree after fitting, that disagreement
is the stated uncertainty.

**Temporal layer (the new part).** At most six parameters. Each exists because a published result says the standard
measures get something wrong, and each can be switched off:

| # | Parameter | The fact it answers to | What the benchmark shows today |
|---|---|---|---|
| 1 | Integration time (attack) | A 5 ms sound needs 18 to 19 dB more than a 200 ms one at moderate levels (Florentine et al. 1996) | Max M gives 16.2 dB by decree of its 0.4 s window; ISO 532-1 gives 9.0 dB on tones |
| 2 | How integration changes with level | The same difference is about 10 dB (tones) and 13 dB (noise) near 100 dB SPL | Max M cannot change with level; ISO 532-1 barely does (9.0 against 11.1 dB) |
| 3 | Weight of what follows the peak (release, tail) | An impact-like envelope is softer than its time reverse (Stecker & Hafter 2000); rising tones are 3 to 5 dB louder than falling ones (Ponsot et al. 2015) | Every energy measure gives exactly 0 dB; ISO 532-1 has the sign, 1.4 dB for the tones |
| 4 | Onset weight and its decay | The first 200 to 300 ms count four to five times as much (Fischenich et al. 2021) | No measure has it; ISO 532-1 and ECMA-418-2 predict the opposite |
| 5 | Carry-over between events | A train is as loud as one impulse up to 0.2 to 0.7 a second, louder above (Ogura et al. 1991) | Max M and ISO 532-1's maximum hold for the slow train; whole-file RMS, LUFS-I and N5 fail by 9 to 41 dB |
| 6 | Low-frequency correction (K-weighted front end only) | A 63 Hz band needs 10 dB more than a 1 kHz band; BS.1770 gives it about 3 (Fenton & Lee 2017) | Max M 1.6 dB, LUFS-I 3.6 dB, ISO 532-1 11.5 dB |

**Decision rule.** The maximum of the smoothed curve over the event, as ISO 532-3 takes the maximum of long-term
loudness, against a high percentile: the data choose.

The simplest member of the family, with every parameter off, is Max M over the event: Playhead's present default.
So the question the data answer is exactly "which of these six does a levelling tool need, and how much does each
buy".

## 4. Fitting and judging

1. **Before any listener data: a model constrained by the literature.** The layer's parameters are fitted to
   published results and tested on published results they were not fitted to. This has value of its own. Every
   measure in use, Max M included, is a formula that has never been tested on sound effects, and the best of them
   reproduces 6 of the 11 results in the benchmark; a layer that reproduces most of them is a better-founded default
   than a 0.4 s window chosen for broadcast programme. It earns the word "validated" under three conditions:
   - **Held-out results.** Six parameters against eleven results, of which seven give a size and four only a sign,
     is a fit. The model is fitted on part of the benchmark and must predict the rest, and published data outside
     it: tone durations at 5 kHz (Buus et al. 1997), temporal weights of level-fluctuating noise (Pedersen &
     Ellermeier 2008), switched noise (Zwicker & Zwicker 1991, used to test the model behind ISO 532-3), and the
     published duration, repetition and asymmetry data reviewed by Rennies et al. (2010).
   - **The papers' own stimuli.** The benchmark's sounds are rebuilt from descriptions; before fitting, each is set
     to the paper's exact parameters.
   - **Ablations.** Each parameter's contribution is reported, and a parameter that buys nothing is dropped.

   What this supports: "reproduces the known loudness of short and changing sounds better than the standard
   measures". What it does not: "predicts the loudness of sound effects". The second claim is the pilot's.
   The job is specified in `docs/LITERATURE_MODEL_BRIEF.md`.
2. **On the pilot's matches.** The literature model enters the pilot as the pre-registered prediction, which makes
   the pilot a test of one hypothesis instead of a comparison of nine measures. Then nested models, from Max M (no
   parameters) upward, one parameter at a time: a parameter is kept or re-fitted only if that lowers the error on
   **held-out items and held-out listeners** (leave one source recording out; leave listeners out), by more than
   the bootstrap interval.
3. **The score** is the pilot's: spread of the residual gain in dB, by group and level, reported between the
   baselines (peak, RMS) and the listeners' own split-half agreement. A model cannot be better than that ceiling;
   if a standard measure already reaches it, the result is "nothing new is needed", and that is published too.
4. **No circularity.** The pilot's items are split into fitting and test sets before anything is fitted, and the
   split is stored with the data. Playhead's tools are never tuned on the model that judges them.
5. **Intervals.** Per stratum (duration, low-frequency share, tail, class), the spread of the held-out residuals
   becomes the prediction interval. An event whose descriptors lie outside the fitted strata is marked
   `outsideDomain`.
6. **Port.** Only the fitted model on the K-weighted front end goes to JavaScript, with parity tests against this
   repository, as the REAPER Lua port is kept equal to `Playhead.levels`.

## 5. Proposed additions to the brief

**Built in this version**

1. **The benchmark of published phenomena** (`listener phenomena`). It turns the research notes into a runnable test,
   shows before any listening what each standard measure gets wrong, and puts each measure's prediction for the
   untested contrasts on record. It is also the regression suite for the fitted model.
2. **Equal-loudness gain as the common unit** (`listener disagree`). Sone models are solved for the gain they imply
   at each playback level, instead of reading phon as dB. On the 56 test effects one dB of gain is worth 0.9 to
   1.1 phon; on a pure low tone at 90 dB SPL it is worth 1.4.
3. **A stated ear convention.** BS.1770 reads the same sound 3.01 dB lower as a mono file than as a two-channel
   file; the hearing models do not. On a corpus that mixes both (18 of the 56 are mono) this alone moves the
   disagreement between Max M and ISO 532-1 from 15.5 to 18.5 dB at the 80 dB level. Comparisons here treat a mono
   file as heard in both ears and say so.

**Proposed for the pilot**

4. **Only redistributable audio** (CC0), so the stimuli are published with the matches, raw trials and scoring
   script, under a DOI. The dataset is then the first of its kind and outlives this model.
5. **Bridge items**: tone pulses, noise bursts and rising and falling tones whose results are known. If the panel
   reproduces them, the results on effects are credible; if not, the setup is at fault. Published impulsive-sound
   matches differ by 5 to 6 dB between two labs, so this check is not optional.
6. **A loudspeaker in front** for the lab pilot: it is the sound field the hearing models assume.
7. **Reference length as a factor** on a subset (1 s against 200 ms): whether a short sound's match depends on it is
   an open question in the notes.
8. **Raw against compressed** versions of a few impacts at equal Max M: a cheap first answer to "does prior
   compression change loudness at equal meter reading", the brief's fifth question.
9. **Pre-registration**: this note's model family, the protocol's analysis plan and the fitting/test split,
   time-stamped before the first session.

**Proposed for the model and the field**

10. **An event rule for single values**, written up as a short technical note for the groups that maintain
    ISO 532-1 and ECMA-418-2: the measured padding dependence of N5 and of the ECMA single values, and a rule (maximum
    over the event, read 20 ms past its end) that removes it.
11. **Evidence on the momentary window for short sounds.** EBU Tech 3341 keeps the 0.4 s window while noting that a
    shorter time constant might be preferable; parameter 1 fitted on effects is direct evidence either way.
12. **Cross-implementation values for ECMA-418-2 on short CC0 sounds.** The standard has no test signals, and its one
    published verification used two outdoor field recordings. The 56 effects measured with two open implementations
    (and with ArtemiS, by anyone who has it) would be the first reference for impulsive material.
13. **A verified JavaScript ISO 532-1.** None exists. Playhead's simplified loudness is right on a 1 kHz tone
    (within 6 % from 40 to 80 dB SPL) and reads white noise 2.7 times too high in sone, about 14 phon: the size of
    its calibration constant, which probably makes up on the tone for the missing slopes between bands. On the test effects
    that puts it a median 17 phon above the full method with a rank correlation of 0.72. The fixtures written here
    are what a full port would be tested against.

## 6. What is deliberately not done

- No model was fitted in version 0.1. The literature-constrained model of section 4 is the next step; its results
  are reported apart from any claim about sound effects until the pilot's data exist.
- Partial loudness, salience, learned metrics, annoyance and hearing-impaired models stay deferred, as in the brief,
  until the pilot shows which loudness representation to build on.
