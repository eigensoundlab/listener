# SPDX-License-Identifier: Apache-2.0
"""What each measure was validated on (rule 2 of the brief). Written into every output file."""

DOMAINS = {
    "bs1770": {
        "validatedOn": "broadcast programme, 336 sequences, r = 0.977 with listener matches (ITU-R BS.1770-5, Attachment 1)",
        "outside": "sound effects; pure tones and narrow-band sounds (the Recommendation says so); anything under 0.4 s",
        "level": "independent of playback level by construction, which hearing is not",
    },
    "iso532_1": {
        "validatedOn": "tones, noises and the technical sounds of ISO 532-1 Annex B (the implementation: within 5 % there)",
        "outside": "sound effects: 4 to 12 dB off on single impulsive sounds in published tests (Sottek and Moll 2015); no onset weighting or decay suppression",
        "level": "depends on the playback level: read each value with its calibration",
    },
    "din45692": {
        "validatedOn": "stationary narrow-band and broadband noises of DIN 45692",
        "outside": "frames quieter than a quarter of the span's maximum are left out; a threshold on sharpness is a regression check, not a perceptual criterion",
        "level": "computed from ISO 532-1 specific loudness, so it shares its calibration",
    },
    "ecma418_2": {
        "validatedOn": "equal-loudness contours and seven technical sounds for roughness (the standard's informative annexes); the implementation against HEAD ArtemiS 15.7 on two field recordings",
        "outside": "short and impulsive sounds: no test signals exist; roughness on spans under 0.5 s",
        "level": "depends on the playback level",
    },
    "literatureL0": {
        "validatedOn": "set from eight published results on tones and noises (duration at two levels, rising against falling, repetition, one low band); tested on seven it was not set from (docs/LITERATURE_MODEL.md)",
        "outside": "sound effects: it has never met a listener's judgement of one. No onset weighting; no masking or loudness summation across frequency; the spectrum enters as one K-weighted level with a fixed low shelf",
        "level": "depends on the playback level; the low-frequency shelf holds near 75 dB SPL",
    },
    "iso532_3": {
        "validatedOn": "dichotic tones, noise bands, switched noise and amplitude-modulated tones (Moore et al. 2016)",
        "outside": "impact sounds are in its scope but not in its validation data; no single value above 5 s",
        "level": "depends on the playback level",
    },
}

NOTES = {
    "integrated-single-block": "span under 0.4 s: 'integrated' is the span's own mean, not a gated value",
    "integrated-ungated": "everything under the -70 LUFS gate: the ungated mean is given",
    "momentary-padded": "span under 0.4 s: Max M counts the span as one window with silence around it",
    "short-term-padded": "span under 3 s: Max S counts the span as one window with silence around it",
    "roughness-short-span": "span under 0.5 s: roughness is outside what the model was built for",
    "no-playhead-document": "no Playhead document: whole-file values only, which misread files with several events or long tails",
    "more-than-two-channels": "more than two channels: the hearing models used the first two as ear signals",
}
