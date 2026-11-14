# Which published results set the literature model, and which test it

Written and committed before the model was fitted. A result moves from "tests" to "sets" only with a note here.

Sources and what was read: `perception_and_measures.md` (the project's research note) for all but the lines marked
*Buus 1997*, which were read in the paper itself on 14 November 2026 (Buus, Florentine & Poulsen 1997, JASA
101(2):669-680, open copy at core.ac.uk). The other papers could not be opened in that session: their stimuli are the
benchmark's rebuilt ones (`listener phenomena`), and the numbers are the notes'.

## Sets the parameters (fit set)

| # | Result | Value | Source |
|---|---|---|---|
| F1 | 1 kHz tone, 5 against 200 ms, 56 dB SPL | 18 to 19 dB | Florentine, Buus & Poulsen 1996 |
| F2 | the same at 100 dB SPL | about 10 dB (9 to 11) | Florentine et al. 1996 |
| F3 | broadband noise, 5 against 200 ms, 76 dB SPL | 18 to 19 dB | Florentine et al. 1996 |
| F4 | the same at 100 dB SPL | about 13 dB (12 to 14) | Florentine et al. 1996 |
| F5 | 1 kHz tone, 30 against 200 ms, at the level of most integration | about 7 dB (6 to 8) | *Buus 1997*, on the 1996 data |
| F6 | 1 kHz tone rising 15 dB against falling 15 dB, 2 s | 3.1 to 5.3 dB | Ponsot, Susini & Meunier 2015 |
| F7 | train of impulses 4 s apart against one impulse | 0 dB (within 1) | Ogura, Suzuki & Sone 1991 |
| F8 | 63 Hz octave band against 1 kHz octave band, 75 dB SPL | 9.98 dB (9 to 11) | Fenton & Lee 2017 |

## Fixed in advance from a paper (not fitted, not a test)

| What | Value | Source |
|---|---|---|
| The loudness function's shape: flattest at moderate levels | exponent near 0.25 at moderate and 0.43 at high levels for 1 kHz | *Buus 1997*; the function used is the "inflected exponential" one of Buus & Florentine, see `literature.py` |
| That a short and a long sound differ by a constant loudness ratio at all levels | the equal-loudness-ratio model | *Buus 1997* |
| How long loudness keeps growing with duration | 0.4 s (growth is still seen from 50 to 250 ms) | *Buus 1997*; Tech 3341's window |

**Changed on 14 November 2026, before fitting and before any held-out result was computed.** This table first held a
third line: an onset weight (the beginning counting 4 to 5 times, decaying over 0.25 s, from Fischenich et al. 2021).
A check on steady tones, which are in no set, showed that with it a steady tone's value depended on its duration by
1.5 dB, and on the fit set's rising and falling tones it made the published result unreachable. Onset weighting is
left out of this version and reported as not modelled. The benchmark's "primacy" row is a test the model is
expected to fail.

## Tests the model (held out)

| # | Result | Value | Source |
|---|---|---|---|
| H1 | 5 kHz tone, 50 against 250 ms, most integration over level | about 9 dB | *Buus 1997* |
| H2 | 5 kHz tone, 10 against 250 ms, most integration over level | about 22 dB | *Buus 1997* |
| H3 | 5 kHz tone, 2 against 250 ms, most integration over level | about 40 dB | *Buus 1997* |
| H4 | 5 kHz tone, 2 against 250 ms, at 60 dB above threshold | 20 to 25 dB | *Buus 1997* |
| H5 | impact-like envelope against its time reverse, tone | reverse louder; 1 to 3 dB from one listener | Stecker & Hafter 2000 |
| H6 | the same, noise | reverse louder | Stecker & Hafter 2000 |
| H7 | train of impulses 0.2 s apart against one impulse | train louder | Ogura et al. 1991 |

Also reported, with no listener data to test against: the three contrasts nobody has measured (dry against wet, boom
against click at two levels).

## Fitted parameters

Planned: four (the exponent of loudness against duration, the strength of decay suppression, the order of a
level-dominant mean, the low-frequency shelf). Fitted in the end: three (two for growth with duration, and the
shelf); `docs/LITERATURE_MODEL.md` says what was dropped and why. Eight numbers set them. Seven results test the
outcome, four of them numbers from one paper at a frequency the model was not fitted at.

## Revision 2, 14 November 2026: after the papers were read

The author approved fetching the papers. Seven were read; Florentine et al. (1996) is behind a paywall and Ogura et
al. (1991) could not be fetched, so for those two only the abstracts were read. The sets did not change. What changed:

- **The sounds of F1 to F5.** In the 1996 paper the level named for the largest temporal integration is the short
  sound's. Each row now holds the 5 ms sound at the named level and asks how far the equally loud 200 ms sound lies
  under it. The tones have the gating the same laboratory states (Buus et al. 1999). F5 puts the 200 ms tone at
  37.5 dB SPL, its level when as loud as the 5 ms tone at 56 dB SPL.
- **The sounds of H1 to H4**: linear 2 ms ramps, as the 1997 paper says.
- **The sounds of H5 and H6**: the envelopes, carriers and level of Stecker & Hafter (2000).
- **The sounds of F8**: octave bands through the filter order of Fenton & Lee (2017).
- **Six results added to the test set, after fitting**: the same paper's octave bands at 125 Hz to 8 kHz (H8 to H13).
  No model was ever fitted to them. Their listeners' values are derived from the paper's table of BS.1770 errors.
- **The model was refitted** on the corrected fit set with the same three free parameters. Its form (which parts
  it has) was chosen on the first revision's stimuli and was not chosen again.

The first revision's results are in `results/literature-model/revision-1/`.
