# SPDX-License-Identifier: Apache-2.0
"""The mapping from digital level to sound pressure.

Every sone-based number depends on the playback level, so a level is never implied. A level is stated the way a room
is calibrated: "a 1 kHz sine that reads REF_LUFS on a BS.1770 meter (one channel) plays at REF_SPL dB SPL". The same
mapping is also written as the level of a full-scale sine, the convention of ISO 532-1 tools, MATLAB and Playhead.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import sqrt

P0 = 2e-5  # Pa
SINE_CREST_DB = 3.0103  # peak over RMS of a sine
DEFAULT_REF_LUFS = -23.0
DEFAULT_REF_SPLS = (70.0, 80.0)


@dataclass(frozen=True)
class Level:
    ref_spl: float            # dB SPL of the reference tone
    ref_lufs: float = DEFAULT_REF_LUFS  # its BS.1770 loudness, measured as one channel

    @property
    def id(self) -> str:
        return f"spl{self.ref_spl:g}"

    @property
    def full_scale_sine_spl(self) -> float:
        # a one-channel 1 kHz sine at L LUFS has an RMS of L dBFS; a full-scale sine has an RMS of -3.01 dBFS
        return self.ref_spl + (-SINE_CREST_DB - self.ref_lufs)

    @property
    def pa_per_fs(self) -> float:
        """Sound pressure in Pa of a sample value of 1.0."""
        return P0 * 10 ** (self.full_scale_sine_spl / 20) * sqrt(2)

    def describe(self) -> dict:
        return {
            "id": self.id,
            "refSpl": self.ref_spl,
            "refLufs": self.ref_lufs,
            "fullScaleSineSpl": round(self.full_scale_sine_spl, 3),
            "paPerFullScale": round(self.pa_per_fs, 6),
            "text": (f"A 1 kHz sine at {self.ref_lufs:g} LUFS (one channel) plays at {self.ref_spl:g} dB SPL; "
                     f"a full-scale sine plays at {self.full_scale_sine_spl:.1f} dB SPL."),
        }


def parse_levels(text: str | None, ref_lufs: float = DEFAULT_REF_LUFS) -> list[Level]:
    vals = DEFAULT_REF_SPLS if not text else [float(v) for v in str(text).split(",") if v.strip()]
    return [Level(v, ref_lufs) for v in vals]


def from_full_scale_sine(spl: float, ref_lufs: float = DEFAULT_REF_LUFS) -> Level:
    return Level(spl - (-SINE_CREST_DB - ref_lufs), ref_lufs)
