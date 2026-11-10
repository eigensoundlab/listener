#!/usr/bin/env sh
# SPDX-License-Identifier: Apache-2.0
# Regenerates every number in docs/FIRST_CHECKS.md and the fixtures for Playhead's tests.
#   sh tools/first_checks.sh <playhead checkout> <MoSQITo checkout> <folder of the 56 effects> [out folder]
# Needs: listener installed (pip install -e .[test,conformance]), node (for playhead analyze), and for ECMA-418-2
# LISTENER_ECMA_PYTHON (see external/README.md).
set -e
PLAYHEAD="$1"; MOSQITO="$2"; SFX="$3"; OUT="${4:-out}"
V="$MOSQITO/validations/sq_metrics"
mkdir -p "$OUT/playhead-docs"
node "$PLAYHEAD/tools/playhead-cli.js" analyze "$SFX" --profile sfx --out-dir "$OUT/playhead-docs"
listener conform --iso532-1 "$V/loudness_zwtv/input/ISO_532-1" --din45692 "$V/sharpness_din/input" --ecma \
  --fixtures fixtures --pretty --out "$OUT/conformance.json"
listener measure "$SFX" --playhead-docs "$OUT/playhead-docs" --levels 60,80 --jobs 2 --out "$OUT/sfx56.listener-measures.json"
listener disagree "$SFX" --playhead-docs "$OUT/playhead-docs" --levels 60,80 --jobs 2 --pick 24 --pretty \
  --out "$OUT/disagreement.json" --report "$OUT/disagreement.md"
listener phenomena --ecma --pretty --out "$OUT/phenomena.json" --report "$OUT/phenomena.md"
node tools/playhead_sone.js "$PLAYHEAD" "$SFX" > "$OUT/playhead-sone.json"
node fixtures/playhead/ebu-conformance-test.js "$PLAYHEAD"
python tools/summarise.py "$OUT" "$PLAYHEAD"
