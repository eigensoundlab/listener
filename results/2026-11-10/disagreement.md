# Where the measures disagree

56 files. Gains are in dB, corpus median removed: what each measure would give a file to make the corpus equally loud. A model stands in for nothing here; the report shows where the choice matters.

- `spl60`: A 1 kHz sine at -23 LUFS (one channel) plays at 60 dB SPL; a full-scale sine plays at 80.0 dB SPL.
- `spl80`: A 1 kHz sine at -23 LUFS (one channel) plays at 80 dB SPL; a full-scale sine plays at 100.0 dB SPL.
- Ears: mono files: BS.1770 values +3.01 dB (heard in both ears); stereo files as measured.
- ISO 532-1 runs on each file after bringing its Max M to the reference loudness of the calibration.

## Pairs of measures

| Measure A | Measure B | Range (dB) | 5th to 95th percentile | A asks most gain for | A asks least gain for |
|---|---|---|---|---|---|
| rms | iso532_1.max@spl60 | 26.4 | 19.9 | perc_till.flac | drum_heavy_kick.flac |
| rms | iso532_1.max@spl80 | 26.1 | 19.5 | perc_till.flac | drum_heavy_kick.flac |
| shortTermMax | iso532_1.max@spl60 | 22.9 | 18.7 | drum_snare_hard.flac | bass_woodsy_c.flac |
| shortTermMax | iso532_1.max@spl80 | 22.6 | 18.5 | drum_snare_hard.flac | bass_woodsy_c.flac |
| peak | shortTermMax | 22.3 | 16.4 | bass_woodsy_c.flac | elec_blip.flac |
| rms | momentaryMax@event | 24.9 | 15.8 | perc_bell.flac | vinyl_hiss.flac |
| momentaryMax@event | iso532_1.max@spl80 | 18.7 | 15.6 | vinyl_scratch.flac | bass_woodsy_c.flac |
| momentaryMax@event | iso532_1.max@spl60 | 19.7 | 15.5 | vinyl_scratch.flac | ambi_piano.flac |
| rms | shortTermMax | 20.3 | 15.1 | perc_bell.flac | drum_heavy_kick.flac |
| integrated | iso532_1.max@spl60 | 19.5 | 14.9 | misc_cineboom.flac | drum_heavy_kick.flac |
| integrated | iso532_1.max@spl80 | 19.4 | 14.7 | misc_cineboom.flac | drum_heavy_kick.flac |
| momentaryMax | iso532_1.max@spl80 | 15.5 | 14.6 | drum_snare_hard.flac | bass_woodsy_c.flac |
| momentaryMax | iso532_1.max@spl60 | 16.9 | 14.3 | drum_snare_hard.flac | ambi_piano.flac |
| peak | iso532_1.max@spl80 | 19.6 | 14.2 | vinyl_rewind.flac | bass_hit_c.flac |
| peak | iso532_1.max@spl60 | 19.2 | 13.9 | vinyl_rewind.flac | bass_hit_c.flac |
| rms | momentaryMax | 22.3 | 13.8 | perc_bell.flac | vinyl_hiss.flac |
| peak | rms | 17.4 | 12.7 | bass_woodsy_c.flac | ambi_lunar_land.flac |
| integrated | shortTermMax | 15.6 | 12.5 | ambi_lunar_land.flac | elec_blip.flac |
| peak | momentaryMax | 20.9 | 10.8 | elec_cymbal.flac | vinyl_hiss.flac |
| peak | momentaryMax@event | 23.5 | 10.8 | elec_cymbal.flac | vinyl_hiss.flac |
| integrated | momentaryMax@event | 14.0 | 9.4 | ambi_lunar_land.flac | vinyl_scratch.flac |
| peak | integrated | 22.4 | 9.0 | elec_cymbal.flac | vinyl_hiss.flac |
| shortTermMax | momentaryMax@event | 10.6 | 8.1 | misc_crow.flac | loop_breakbeat.flac |
| integrated | momentaryMax | 12.9 | 8.0 | ambi_lunar_land.flac | elec_blip.flac |
| rms | integrated | 17.1 | 7.7 | perc_bell.flac | vinyl_hiss.flac |
| momentaryMax | shortTermMax | 7.9 | 6.9 | ambi_drone.flac | bass_hit_c.flac |
| momentaryMax | momentaryMax@event | 4.5 | 2.7 | ambi_dark_woosh.flac | loop_breakbeat.flac |
| iso532_1.max@spl60 | iso532_1.max@spl80 | 2.1 | 1.4 | ambi_piano.flac | perc_snap.flac |

## Files, most disputed first

| File | Event (s) | Class | Low | Tail (s) | Spread | ISO − Max M @spl60 | ISO − Max M @spl80 | I − Max M | Peak − Max M |
|---|---|---|---|---|---|---|---|---|---|
| drum_heavy_kick.flac | 0.229 | impulse | 0.98 | 0.194 | 17.87 | +8.4 | +8.7 | -5.0 | -2.7 |
| vinyl_hiss.flac | 0.186 | impulse | 0.48 | 3.452 | 17.12 | -6.5 | -5.8 | -0.6 | -15.1 |
| bass_woodsy_c.flac | 3.233 | sustained | 0.96 | 2.438 | 14.38 | +8.9 | +9.4 | -1.7 | +5.3 |
| ambi_piano.flac | 0.74 | sustained | 0.98 | 1.702 | 14.09 | +9.9 | +9.4 | -1.1 | +4.6 |
| bass_hit_c.flac | 0.255 | iterative | 0.82 | 0.248 | 13.93 | +6.6 | +7.5 | -1.4 | -4.6 |
| elec_blip.flac | 0.16 | impulse | 0.00 | 0.068 | 12.9 | -5.1 | -4.2 | -7.3 | -9.9 |
| loop_breakbeat.flac | 0.125 | impulse | 0.97 | 0.244 | 11.96 | +2.2 | +1.9 | -2.7 | +0.7 |
| elec_ping.flac | 0.206 | impulse | 0.00 | 0.194 | 11.58 | +3.5 | +4.2 | -6.0 | -2.6 |
| perc_bell.flac | 1.335 | sustained | 0.00 | 0.666 | 11.52 | +7.7 | +8.1 | +4.6 | +4.8 |
| ambi_drone.flac | 3.126 | sustained | 0.00 | 3.244 | 11.31 | +6.5 | +6.4 | -2.2 | +2.0 |
| vinyl_scratch.flac | 0.11 | impulse | 0.55 | 0.084 | 10.4 | -6.2 | -5.7 | -4.9 | -0.3 |
| ambi_glass_hum.flac | 9.404 | sustained | 0.00 | 4.514 | 10.13 | +5.8 | +6.6 | +1.0 | +5.4 |
| drum_snare_hard.flac | 0.221 | impulse | 0.01 | 0.182 | 10.03 | -7.0 | -6.1 | -3.2 | +0.2 |
| elec_bell.flac | 0.276 | impulse | 0.00 | 0.246 | 9.82 | +1.2 | +1.6 | -4.8 | -0.8 |
| ambi_lunar_land.flac | 7.396 | sustained | 0.00 | 4.716 | 9.59 | +7.9 | +9.1 | +5.6 | +1.2 |
| elec_fuzz_tom.flac | 0.371 | sustained | 0.91 | 0.322 | 9.49 | -0.1 | +1.2 | -3.6 | +1.4 |
| perc_swash.flac | 0.27 | impulse | 0.01 | 0.176 | 9.27 | -1.9 | -1.3 | -4.2 | -6.2 |
| misc_burp.flac | 0.427 | iterative | 0.09 | 0.21 | 9.18 | -6.2 | -5.5 | -2.1 | +0.4 |
| loop_amen.flac | 0.209 | impulse | 0.40 | 0.408 | 9.11 | -6.4 | -6.0 | -1.6 | -1.5 |
| ambi_glass_rub.flac | 2.003 | sustained | 0.00 | 1.586 | 9.07 | +5.3 | +4.8 | -1.3 | +4.6 |
| perc_snap.flac | 0.18 | impulse | 0.10 | 0.164 | 8.85 | -2.7 | -1.2 | -4.4 | -5.8 |
| glitch_perc5.flac | 0.525 | sustained | 0.01 | 0.286 | 8.83 | -5.8 | -4.9 | -0.7 | -1.2 |
| perc_till.flac | 0.56 | iterative | 0.02 | 0.49 | 8.83 | -2.5 | -1.9 | +1.4 | +0.1 |
| vinyl_rewind.flac | 0.627 | iterative | 0.11 | 1.538 | 8.02 | -4.3 | -3.7 | -1.8 | +3.7 |
| glitch_perc4.flac | 0.531 | sustained | 0.00 | 0.348 | 8.01 | -5.0 | -3.9 | -0.1 | -2.9 |
| elec_cymbal.flac | 0.467 | sustained | 0.00 | 0.274 | 7.94 | +2.2 | +3.0 | -2.1 | +5.9 |
| vinyl_backspin.flac | 0.914 | iterative | 0.18 | 0.676 | 7.67 | -5.5 | -4.8 | -0.8 | +1.6 |
| elec_wood.flac | 0.212 | impulse | 0.34 | 0.282 | 7.62 | -4.6 | -3.9 | -3.2 | -3.0 |
| ambi_soft_buzz.flac | 0.784 | sustained | 0.18 | 0.334 | 7.34 | +4.0 | +4.5 | -2.5 | +0.3 |
| drum_splash_hard.flac | 1.805 | sustained | 0.00 | 1.02 | 7.22 | -1.9 | -0.9 | +1.0 | +4.3 |
| ambi_sauna.flac | 8.406 | sustained | 0.05 | 7.202 | 6.98 | -3.8 | -3.3 | +1.4 | +1.7 |
| loop_industrial.flac | 0.453 | sustained | 0.59 | 0.362 | 6.86 | -4.8 | -4.3 | -1.5 | +0.9 |
| glitch_perc2.flac | 0.476 | impulse | 0.84 | 0.258 | 6.71 | -1.0 | -0.7 | -0.5 | -2.6 |
| elec_chime.flac | 1.544 | sustained | 0.00 | 0.96 | 6.63 | +4.5 | +5.1 | +3.1 | +4.5 |
| loop_garzul.flac | 0.244 | sustained | 0.56 | 3.358 | 6.31 | -4.1 | -3.8 | -1.6 | +0.7 |
| misc_crow.flac | 0.424 | sustained | 0.00 | 0.256 | 6.27 | -1.5 | -0.1 | -3.2 | +1.8 |
| glitch_perc1.flac | 0.189 | impulse | 0.65 | 0.648 | 6.23 | -3.4 | -2.6 | +1.5 | -1.2 |
| ambi_swoosh.flac | 1.829 | sustained | 0.31 | 0.618 | 6.16 | +4.6 | +4.9 | +0.3 | +1.3 |
| misc_cineboom.flac | 6.908 | sustained | 0.88 | 2.734 | 6.14 | -5.9 | -5.4 | +0.3 | +0.3 |
| ambi_haunted_hum.flac | 8.858 | sustained | 0.86 | 3.198 | 5.86 | +0.5 | +0.6 | +1.7 | +2.9 |
| glitch_bass_g.flac | 0.125 | impulse | 0.70 | 1.306 | 5.69 | +4.8 | +4.8 | +2.5 | +1.8 |
| glitch_perc3.flac | 0.609 | sustained | 0.01 | 0.278 | 5.66 | -3.0 | -2.3 | -1.1 | -2.1 |
| ambi_dark_woosh.flac | 3.111 | sustained | 0.63 | 1.246 | 5.62 | +5.1 | +5.1 | +1.1 | +0.2 |
| glitch_robot2.flac | 0.842 | iterative | 0.03 | 0.208 | 5.57 | -3.3 | -2.9 | -2.1 | +2.2 |
| guit_e_slide.flac | 1.71 | sustained | 0.00 | 1.184 | 5.55 | +2.0 | +2.6 | +3.0 | +4.5 |
| drum_tom_lo_hard.flac | 0.874 | sustained | 0.90 | 0.376 | 5.53 | +1.5 | +2.2 | +1.4 | +3.3 |
| elec_twang.flac | 0.601 | sustained | 0.06 | 0.386 | 5.21 | -2.2 | -1.5 | -0.5 | -2.2 |
| drum_cymbal_open.flac | 1.228 | sustained | 0.00 | 0.924 | 5.12 | -0.5 | +0.5 | +3.1 | +3.3 |
| glitch_robot1.flac | 0.964 | iterative | 0.04 | 0.148 | 5.05 | -4.6 | -4.1 | -2.4 | -0.5 |
| guit_em9.flac | 0.755 | sustained | 0.44 | 3.15 | 4.77 | -1.5 | -1.1 | +1.9 | +2.1 |
| guit_harmonics.flac | 2.885 | iterative | 0.00 | 0.804 | 4.09 | -0.4 | +0.2 | +0.3 | -3.1 |
| guit_e_fifths.flac | 0.502 | sustained | 0.02 | 2.034 | 3.51 | -1.1 | -0.7 | +1.8 | +2.3 |
| bass_drop_c.flac | 2.36 | sustained | 0.55 | 1.382 | 3.49 | -2.6 | -2.3 | -0.1 | +0.5 |
| drum_roll.flac | 0.337 | sustained | 0.02 | 5.882 | 3.35 | -2.8 | -2.5 | +0.5 | -1.6 |
| loop_mika.flac | 2.508 | iterative | 0.51 | 2.38 | 3.23 | -1.7 | -1.3 | -0.4 | -0.8 |
| ambi_choir.flac | 1.515 | sustained | 0.00 | 0.624 | 2.86 | +1.6 | +2.4 | +0.0 | +2.0 |

## Proposed stimuli

| File | Duration | Low-frequency | Long tail | Spread (dB) |
|---|---|---|---|---|
| drum_heavy_kick.flac | 50 to 400 ms | yes | no | 17.87 |
| vinyl_hiss.flac | 50 to 400 ms | yes | yes | 17.12 |
| bass_woodsy_c.flac | over 2 s | yes | yes | 14.38 |
| ambi_piano.flac | 0.4 to 2 s | yes | yes | 14.09 |
| elec_blip.flac | 50 to 400 ms | no | no | 12.9 |
| perc_bell.flac | 0.4 to 2 s | no | no | 11.52 |
| ambi_drone.flac | over 2 s | no | yes | 11.31 |
| vinyl_rewind.flac | 0.4 to 2 s | no | yes | 8.02 |
| loop_industrial.flac | 0.4 to 2 s | yes | no | 6.86 |
| guit_harmonics.flac | over 2 s | no | no | 4.09 |
| drum_roll.flac | 50 to 400 ms | no | yes | 3.35 |
| bass_hit_c.flac | 50 to 400 ms | yes | no | 13.93 |
| loop_garzul.flac | 50 to 400 ms | yes | yes | 6.31 |
| misc_cineboom.flac | over 2 s | yes | yes | 6.14 |
| guit_em9.flac | 0.4 to 2 s | yes | yes | 4.77 |
| elec_ping.flac | 50 to 400 ms | no | no | 11.58 |
| misc_burp.flac | 0.4 to 2 s | no | no | 9.18 |
| ambi_glass_hum.flac | over 2 s | no | yes | 10.13 |
| drum_splash_hard.flac | 0.4 to 2 s | no | yes | 7.22 |
| glitch_perc2.flac | 0.4 to 2 s | yes | no | 6.71 |
| loop_breakbeat.flac | 50 to 400 ms | yes | no | 11.96 |
| glitch_bass_g.flac | 50 to 400 ms | yes | yes | 5.69 |
| ambi_haunted_hum.flac | over 2 s | yes | yes | 5.86 |
| drum_snare_hard.flac | 50 to 400 ms | no | no | 10.03 |
