# Recording raw takes for the dataset

A way to record common sound effects so that every file in the dataset has a known history: what was recorded, with
what, and that nothing was done to it afterwards. REAPER is used to record and to mark the takes; the takes are cut
outside REAPER, sample for sample.

What makes a recording usable here is not an expensive microphone. It is that the chain is written down, nothing
clips, and nothing levels or limits the signal.

## The chain

| Part | Setting | Why |
|---|---|---|
| Microphone | 30 to 100 cm from the sound, the distance in `shotlist.csv`; the same for all strengths of one sound | Closer than 30 cm a directional microphone adds bass (proximity effect) |
| Interface | Microphone on the XLR input; 48 V on for a condenser, off for a dynamic; gain so the hardest hit peaks between −12 and −6 dB | 24-bit recording has room to spare: headroom costs nothing, clipping costs the take |
| Gain knob | Left alone for all strengths of one sound, and written into `session.json` | Soft, medium and hard then differ as they did in the room |
| REAPER | 48 kHz, WAV 24 bit PCM, mono, no FX, no monitoring through REAPER | The models work at 48 kHz; mono is what the listening test plays |
| Room | The quietest one, soft furnishings, windows closed, fridge and fans off, phone silent | The room tone sets how long a tail can be followed |

**If the microphone connects by USB**, it does not go through the interface: it is its own recorder. Check that its
driver or app has no noise reduction, limiter or automatic gain switched on, and write the USB connection into
`session.json`. Some USB microphones record 16 bit; that is acceptable and will show in the manifest.

**What a small microphone cannot do:** record below about 50 to 80 Hz as it was. The three "boom" sounds in the shot
list are the lowest it can take. Deep booms for the test come from synthesis or from existing CC0 recordings.

## Before the first session

1. In REAPER: *Actions > Show action list > New action > Load ReaScript*, and load the three files in `reaper/`.
2. Make a folder for the session, save an empty project in it, and run **Listener - Set up recording project**. It
   sets 48 kHz, a folder `raw` for the recordings and an armed mono track on input 1, and lists what to check by hand
   (the recording format above all: *File > Project settings > Media*, WAV, 24 bit PCM).
3. Copy `session.example.json` to `session.json` in the session's folder and fill it in.

## A session

1. **Room tone.** Record 10 s of the silent room at the session's gain. Name that item `roomtone_-_01` (select it,
   run **Listener - Name takes**, id `roomtone`, strength `-`).
2. **One sound at a time**, from `shotlist.csv`. Set the gain on the hardest version, then record everything for that
   sound in one pass: five or more of each strength, two seconds of quiet between takes, soft first.
3. **Split the pass into takes.** Either by hand (S at each gap), or with Playhead's *Split items at sounds*, which
   cuts a few milliseconds before each attack and ends each piece where the sound has died away, with a short fade.
   Leave at least 10 ms before the attack. Delete the pieces that went wrong.
4. **Name the takes.** Select the takes of one strength and run **Listener - Name takes**: the id from the shot list
   and the strength. They become `knock-table_soft_01`, `_02` and so on; numbering goes on where it stopped.
5. **Do not change anything else**: no item gain, no normalising, no stretching, no FX. A fade at the end of an item
   is fine and is recorded.
6. When the session is done, run **Listener - Export take list**. It writes `takes.csv` next to the project.

## Cutting and checking

```sh
listener takes takes.csv --session session.json --out takes
```

This copies each take's samples out of the raw file (no gain, no resampling, no dither; only the item's fade), and
writes `takes/manifest.json` with every file's checksum, origin, levels and findings:

| Finding | Means | Do |
|---|---|---|
| `clipped` | Flat top at full scale | Record again with less gain |
| `hot` | Peak above −3 dBFS | Usable; less gain next time |
| `starts-loud` | Loud within the first 2 ms | The cut is in the attack: move the item's start earlier and export again |
| `ends-loud` | Loud in the last 5 ms without a fade | The tail is cut: lengthen the item or give it a fade |
| `dc-offset` | The waveform is not centred | Check the chain |
| `near-room-tone` | Peak less than 40 dB above the room | Too quiet for this room: closer, or a quieter room |

A take that had a gain, a play rate, FX or a reversed source in REAPER is refused, with the reason.

## What goes where

- **The dataset** (not this repository): `takes/` with its manifest, the raw files, `session.json` and the REAPER
  project. Published under CC0 as its own record, with its own DOI.
- **This repository:** the method (this folder), and later the dataset's manifest with a script that fetches the audio.

## Not yet tried in REAPER

The three actions were written from REAPER's API documentation and run in Lua 5.4 against a stand-in for the API
(`tests/test_reaper_scripts.py`). They have not been run in REAPER itself. Try them on a throwaway project first.
