# Pilot listening test: loudness of one-shot sound effects

**Status: draft for the author's review. Nobody listens before it is reviewed and its analysis plan is frozen.**

## The question

Which measure brings a set of sound effects closest to equal loudness for listeners: peak, RMS, LUFS-I, Max M, Max S,
ISO 532-1 (maximum, N5), ECMA-418-2 (maximum), ISO 532-3 (maximum long-term loudness, if its code is available), or
Playhead's event-aware measures? No published study answers this for sound effects.

## Design in one paragraph

Each listener matches every item to one fixed reference, once per repeat, by adjusting the item's level. The matches
are the data: one number per listener, item, level and repeat. Every measure, present or future, is then scored
offline against the same matches, so no measure is favoured by the procedure and a new measure needs no new test.

## Listeners

- 12 to 16, each doing both playback levels. Published matching studies used 8 to 20.
- Self-reported normal hearing; an audiogram where the lab has one. Age band and audio experience are recorded.
- Written consent before the session. An anonymous code per listener; no name, address or device identifier is
  stored with the data. A listener can stop at any time and have their data removed until publication.

## Playback

- **Lab pilot: one loudspeaker in front of the listener**, in a quiet treated room, all items mono. This is the
  sound field ISO 532-1 and ECMA-418-2 assume (free field, frontal), and it avoids the headphone's own response.
  Headphones are the fallback: the same model for everyone, its level measured on a coupler or artificial ear, and
  the results labelled as headphone data.
- **Two levels**, stated as the calibration in `listener-measures`: a 1 kHz tone at −23 LUFS plays at **60** and at
  **80 dB SPL** at the listening position. Measured with a sound level meter (Z-weighted, slow) before each
  session and written into the result file, with the meter's model and the room's background level.
- Order of the two levels balanced across listeners; a break between them.

## Items (72 to 96)

All from sources that allow redistribution (CC0), so the audio is published with the matches. All mono, 48 kHz.
Before the test every item is set to Max M = −23 LUFS, then shifted by a random offset of ±10 dB for each trial.

| Group | Items | Why |
|---|---|---|
| Disputed real effects | 36 to 48 | Chosen by `listener disagree --pick` from a CC0 effects corpus, spread over duration (under 50 ms, 50 to 400 ms, 0.4 to 2 s, over 2 s), low-frequency share and tail length |
| Dry and wet | 6 impacts × (dry, tail of 0.5 s, 1.5 s, 3 s) = 24 | Tail handling; no listener data exist |
| Reversed | 6 of the dry impacts and 2 risers, time-reversed | Rise and fall asymmetry, decay suppression |
| Rate | 2 footsteps × (single, 0.5, 2 and 4 a second) = 8 | Ogura's critical rate on real sounds |
| Booms | 6 low-frequency one-shots | Low-frequency weighting; the level-dependent group |
| Raw and compressed | 4 impacts × (raw, 4:1 compressed, limited 6 dB) = 12 | Whether denser sounds are louder at equal Max M |
| Bridge | 1 kHz tone pulses of 10, 50 and 500 ms; noise bursts of 5, 30 and 200 ms; a 2 s tone rising and falling 15 dB = 8 | Results known from the literature: if the panel does not reproduce them, the setup is at fault, not the effects |

The upper counts give about 100 items; drop to 72 by using 36 disputed effects, 4 impacts for dry and wet, and 2
compressed impacts.

**Reference:** steady pink noise, 1 s with 20 ms ramps, at −23 LUFS, fixed for the whole test.
**Reference control:** 12 items are also matched to a short reference (the same noise, 200 ms). Whether matches of
short sounds depend on the reference's length is an open question; if they do, the main result is reported for both.

## Procedure

- Method of adjustment. A trial plays reference, 500 ms of silence, item, and repeats until the listener is done.
  A knob or keys change the item's level in 0.5 dB steps (0.1 dB with a modifier). No level is shown.
- Two repeats per item and level, one starting above and one below (random start within ±10 dB).
- Items in random order, a different order for each listener; bridge items spread through the session.
- Training: 8 trials that are not analysed.
- Time: 96 items × 2 repeats × 2 levels at about 20 s is roughly two hours: two sessions on different days, or
  72 items in one long session with two breaks.

**Online version** (webMUSHRA with headphone screening after Woods et al. 2017 and Milne et al. 2021): the same items
and procedure, one level set by the listener to a comfortable value. The absolute level is unknown, so the online
data support only conclusions that do not depend on level, and they are analysed apart from the lab data.

## Analysis plan (frozen before the first session)

1. **Ground truth.** For each item and level: the mean over listeners of the matched gain, relative to the item's
   Max M-normalised level. Listener means are centred first, so a listener who sets everything high does not count.
2. **Each measure's prediction.** The gain the measure would give the item to equal the reference. For sone-based
   measures the gain is solved for at the measured playback level (`Zwicker.gain_for_level`), not read off in phon.
3. **Score.** The spread of what is left: standard deviation and RMS of (ground truth − prediction), with the mean
   removed. Also the share of items within ±1 dB and ±2 dB, and the 95th percentile of the absolute error. By group
   and by level.
4. **Fairness.** Every measure gets the same per-group offsets Playhead's rules get, so no measure wins by having
   more settings. Measures are not tuned on these data. A model fitted to them (version 2) is scored only on
   held-out items and held-out listeners.
5. **Uncertainty.** Bootstrap over listeners and over items; a difference between two measures counts when its 95 %
   interval excludes zero.
6. **Ceiling and baselines.** The split-half agreement of the listeners is the best any measure can do; peak and RMS
   are the baselines. Every score is reported between the two.
7. **Checks.** The bridge items against their published values (tone pulses, 5 against 200 ms noise, rising against
   falling). A listener whose two repeats differ by more than 4 dB on more than a fifth of the items is left out;
   the rule is applied before looking at any measure's score.
8. **Stated in advance.** The smallest difference the pilot can resolve: with a standard error of about 0.3 to
   0.5 dB per item and 72 or more items, about 0.5 dB RMS between two measures. This is an estimate from published
   listener spreads, not a power analysis; the pilot's own spread replaces it.

## What is recorded

One file per session, `"format": "listener-matches"`, version 1: protocol version, date, room and playback chain,
the measured calibration, the listener's anonymous code with age band and experience, and one row per trial (item,
level, repeat, start offset, matched gain, number of adjustments, time). Published with the audio and the scoring
script under an open licence once the listeners' consent covers it.

## Open points for the author

1. Loudspeaker or headphones for the lab pilot, and which room and meter.
2. The effects corpus the disputed items come from. The 56 Sonic Pi samples are a test set (drums, loops,
   ambiences), not a sound-effects library; `docs/FIRST_CHECKS.md` lists what `listener disagree` would pick from
   them only to show the method.
3. Where the reverberant tails come from: a measured impulse response under CC0, or decaying noise with a stated
   decay time (repeatable, less natural).
4. Whether two sessions per listener are acceptable, or the item count drops to 72.
5. Whether ISO 532-3's code is bought, so its maximum long-term loudness can be scored.
